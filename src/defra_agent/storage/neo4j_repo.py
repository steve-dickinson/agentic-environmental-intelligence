"""Neo4j repository for environmental knowledge graph.

This module provides graph-based storage and querying for environmental
incidents, monitoring stations, permits, and their relationships.
"""

from datetime import datetime
from typing import Any

from neo4j import GraphDatabase, ManagedTransaction

from defra_agent.config import settings
from defra_agent.domain.models import Incident


class EnvironmentalGraphRepository:
    """Neo4j repository for environmental knowledge graph.

    Stores incidents as connected graphs with:
    - Incident nodes
    - MonitoringStation nodes
    - Reading nodes (connecting incidents to stations)
    - Permit nodes
    - Spatial relationships (NEAR_PERMIT, UPSTREAM_OF, etc.)
    - Temporal relationships (BEFORE, AFTER, CORRELATES_WITH)
    """

    def __init__(self) -> None:
        """Initialize Neo4j driver connection."""
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        """Close Neo4j driver connection."""
        self._driver.close()

    def verify_connection(self) -> bool:
        """Verify Neo4j connection is working.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self._driver.session() as session:
                result = session.run("RETURN 1 as num")
                record = result.single()
                return record is not None and record["num"] == 1
        except Exception as e:
            print(f"Neo4j connection failed: {e}")
            return False

    def initialize_schema(self) -> None:
        """Create constraints and indexes for the graph schema.

        This should be run once during setup to ensure optimal query performance
        and data integrity.
        """
        with self._driver.session() as session:
            # Constraints for uniqueness
            session.run(
                "CREATE CONSTRAINT station_id_unique IF NOT EXISTS "
                "FOR (s:MonitoringStation) REQUIRE s.station_id IS UNIQUE"
            )

            session.run(
                "CREATE CONSTRAINT incident_id_unique IF NOT EXISTS "
                "FOR (i:Incident) REQUIRE i.incident_id IS UNIQUE"
            )

            session.run(
                "CREATE CONSTRAINT permit_id_unique IF NOT EXISTS "
                "FOR (p:Permit) REQUIRE p.permit_id IS UNIQUE"
            )

            # Indexes for performance
            session.run(
                "CREATE POINT INDEX station_location IF NOT EXISTS "
                "FOR (s:MonitoringStation) ON (s.location)"
            )

            session.run(
                "CREATE INDEX incident_timestamp IF NOT EXISTS FOR (i:Incident) ON (i.timestamp)"
            )

            session.run(
                "CREATE INDEX reading_timestamp IF NOT EXISTS FOR (r:Reading) ON (r.timestamp)"
            )

            session.run(
                "CREATE INDEX incident_priority IF NOT EXISTS FOR (i:Incident) ON (i.priority)"
            )

            print("✅ Neo4j schema initialized (constraints + indexes created)")

    def store_incident_graph(self, incident: Incident) -> None:
        """Store incident as a connected graph structure.

        Idempotent: Skips if incident already exists in graph.

        Creates:
        - Incident node with metadata
        - Reading nodes for each sensor reading
        - MonitoringStation nodes (merged if already exist)
        - Permit nodes (merged if already exist)
        - Relationships: HAS_READING, AT_STATION, NEAR_PERMIT

        Args:
            incident: Incident object to store in graph
        """
        # Check if incident already exists
        result = self._driver.execute_query(
            "MATCH (i:Incident {incident_id: $incident_id}) RETURN count(i) as count",
            incident_id=incident.id,
        )

        if result.records[0]["count"] > 0:
            # Already stored, skip
            return

        with self._driver.session() as session:
            session.execute_write(self._create_incident_subgraph, incident)

    def _create_incident_subgraph(self, tx: ManagedTransaction, incident: Incident) -> None:
        """Transaction function to create incident subgraph.

        Args:
            tx: Neo4j transaction
            incident: Incident to store
        """
        # 1. Create Incident node
        if incident.alerts:
            alert_priority = incident.alerts[0].priority
            # Handle both AlertPriority enum and string
            if hasattr(alert_priority, "value"):
                priority_str = alert_priority.value
            else:
                priority_str = str(alert_priority)
            summary_str = incident.alerts[0].summary
        else:
            priority_str = "unknown"
            summary_str = ""

        tx.run(
            """
            CREATE (i:Incident {
                incident_id: $incident_id,
                timestamp: datetime($timestamp),
                priority: $priority,
                summary: $summary,
                created_at: datetime()
            })
            """,
            incident_id=incident.id,
            timestamp=datetime.now().isoformat(),
            priority=priority_str,
            summary=summary_str,
        )

        # 2. Create Reading nodes + MonitoringStation nodes + relationships
        for reading in incident.readings:
            # Skip readings without coordinates
            if reading.lat is None or reading.lon is None:
                continue

            tx.run(
                """
                // Merge station (create if not exists, update if exists)
                MERGE (s:MonitoringStation {station_id: $station_id})
                ON CREATE SET
                    s.lat = $lat,
                    s.lon = $lon,
                    s.location = point({latitude: $lat, longitude: $lon}),
                    s.source = $source,
                    s.created_at = datetime()
                ON MATCH SET
                    s.last_seen = datetime()

                // Find the incident we just created
                WITH s
                MATCH (i:Incident {incident_id: $incident_id})

                // Create reading node
                CREATE (r:Reading {
                    value: $value,
                    timestamp: datetime($timestamp),
                    source: $source
                })

                // Create relationships
                CREATE (i)-[:HAS_READING]->(r)
                CREATE (r)-[:AT_STATION]->(s)
                """,
                station_id=reading.station_id,
                lat=reading.lat,
                lon=reading.lon,
                source=reading.source or "unknown",
                incident_id=incident.id,
                value=reading.value,
                timestamp=reading.timestamp.isoformat(),
            )

        # 3. Create Permit nodes + NEAR_PERMIT relationships
        if incident.permits:
            for permit in incident.permits:
                tx.run(
                    """
                    // Merge permit (create if not exists)
                    MERGE (p:Permit {permit_id: $permit_id})
                    ON CREATE SET
                        p.operator = $operator,
                        p.permit_type = $permit_type,
                        p.postcode = $postcode,
                        p.address = $address,
                        p.created_at = datetime()

                    // Find incident
                    WITH p
                    MATCH (i:Incident {incident_id: $incident_id})

                    // Create NEAR_PERMIT relationship with distance
                    MERGE (i)-[r:NEAR_PERMIT]->(p)
                    ON CREATE SET r.distance_km = $distance_km
                    """,
                    permit_id=permit.permit_id,
                    operator=permit.operator_name,
                    permit_type=permit.registration_type or "unknown",
                    postcode=permit.site_postcode,
                    address=permit.site_address,
                    incident_id=incident.id,
                    distance_km=permit.distance_km,
                )

        print(f"✅ Stored incident {incident.id} in Neo4j graph")

    def find_upstream_permits(self, incident_id: str, max_hops: int = 3) -> list[dict[str, Any]]:
        """Find permits upstream of incident location using multi-hop queries.

        This demonstrates graph advantage: RAG cannot trace spatial relationships
        through multiple hops.

        Args:
            incident_id: Incident to analyze
            max_hops: Maximum hops upstream to search (default 3)

        Returns:
            List of upstream permits with path information

        Example:
            >>> repo = EnvironmentalGraphRepository()
            >>> upstream = repo.find_upstream_permits("abc-123", max_hops=3)
            >>> for permit in upstream:
            ...     print(f"{permit['operator']} ({permit['hops']} hops)")
            Wessex Water (1 hops)
            Somerset Council (2 hops)
        """
        # Build Cypher query with max_hops as part of the pattern string
        query = f"""
                // Find incident and its stations
                MATCH (i:Incident {{incident_id: $incident_id}})
                      -[:HAS_READING]->(:Reading)
                      -[:AT_STATION]->(station:MonitoringStation)

                // Find permits connected to incident
                MATCH (i)-[:NEAR_PERMIT]->(permit:Permit)

                // Try to find upstream path (if FLOWS_TO relationships exist)
                // This is a placeholder - in production, you'd have actual flow topology
                OPTIONAL MATCH path = (permit)-[:UPSTREAM_OF*1..{max_hops}]->(station)

                RETURN DISTINCT
                    permit.permit_id as permit_id,
                    permit.operator as operator,
                    permit.permit_type as permit_type,
                    CASE
                        WHEN path IS NOT NULL THEN length(path)
                        ELSE 0
                    END as hops,
                    CASE
                        WHEN path IS NOT NULL
                        THEN [node in nodes(path) | coalesce(node.station_id, node.name)]
                        ELSE []
                    END as path_nodes
                ORDER BY hops ASC
                """

        with self._driver.session() as session:
            result = session.run(query, incident_id=incident_id)

            permits = []
            for record in result:
                permits.append(
                    {
                        "permit_id": record["permit_id"],
                        "operator": record["operator"],
                        "permit_type": record["permit_type"],
                        "hops": record["hops"],
                        "path_nodes": record["path_nodes"],
                    }
                )

            return permits

    def find_similar_incidents_by_structure(
        self, incident_id: str, max_distance_km: float = 10.0, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Find structurally similar incidents using graph patterns.

        Unlike RAG semantic search, this finds incidents with similar STRUCTURE:
        - Similar number of affected stations
        - Similar spatial distribution
        - Similar permit context

        Args:
            incident_id: Incident to find matches for
            max_distance_km: Maximum distance for spatial matching (meters)
            limit: Maximum results to return

        Returns:
            List of structurally similar incidents
        """
        with self._driver.session() as session:
            result = session.run(
                """
                // Get current incident structure
                MATCH (current:Incident {incident_id: $incident_id})
                      -[:HAS_READING]->(:Reading)
                      -[:AT_STATION]->(s1:MonitoringStation)

                WITH current,
                     count(DISTINCT s1) as num_stations,
                     collect(DISTINCT s1.location) as locations

                // Find other incidents
                MATCH (other:Incident)-[:HAS_READING]->(:Reading)
                                      -[:AT_STATION]->(s2:MonitoringStation)

                WHERE other.incident_id <> current.incident_id
                  AND other.timestamp > current.timestamp - duration('P90D')

                WITH current, num_stations, locations,
                     other,
                     count(DISTINCT s2) as other_num_stations,
                     collect(DISTINCT s2.location) as other_locations

                // Calculate spatial similarity
                WITH current, other,
                     num_stations, other_num_stations,
                     reduce(matches = 0, loc1 in locations |
                       matches + reduce(m = 0, loc2 in other_locations |
                         m + CASE
                           WHEN point.distance(loc1, loc2) < $max_distance_m
                           THEN 1 ELSE 0
                         END
                       )
                     ) as spatial_matches

                WHERE abs(num_stations - other_num_stations) <= 2
                  AND spatial_matches > 0

                RETURN
                    other.incident_id as incident_id,
                    other.timestamp as timestamp,
                    other.summary as summary,
                    other.priority as priority,
                    spatial_matches as matching_stations,
                    abs(num_stations - other_num_stations) as station_diff
                ORDER BY spatial_matches DESC, timestamp DESC
                LIMIT $limit
                """,
                incident_id=incident_id,
                max_distance_m=max_distance_km * 1000,
                limit=limit,
            )

            incidents = []
            for record in result:
                incidents.append(
                    {
                        "incident_id": record["incident_id"],
                        "timestamp": record["timestamp"],
                        "summary": record["summary"],
                        "priority": record["priority"],
                        "matching_stations": record["matching_stations"],
                        "station_diff": record["station_diff"],
                    }
                )

            return incidents

    def get_incident_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge graph.

        Returns:
            Dictionary with node counts, relationship counts, etc.
        """
        with self._driver.session() as session:
            # Count nodes by type
            node_counts = session.run(
                """
                MATCH (n)
                RETURN labels(n)[0] as type, count(*) as count
                ORDER BY count DESC
                """
            )

            stats: dict[str, Any] = {"nodes": {}}
            for record in node_counts:
                stats["nodes"][record["type"]] = record["count"]

            # Count relationships by type
            rel_counts = session.run(
                """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
                """
            )

            stats["relationships"] = {}
            for record in rel_counts:
                stats["relationships"][record["type"]] = record["count"]

            return stats
