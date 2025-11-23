// Neo4j Schema Initialization for Environmental Intelligence
// Run after container startup to create constraints and indexes

// ============================================================================
// CONSTRAINTS (Enforce uniqueness and data integrity)
// ============================================================================

// Monitoring Stations
CREATE CONSTRAINT station_id_unique IF NOT EXISTS
FOR (s:MonitoringStation) REQUIRE s.station_id IS UNIQUE;

// Incidents
CREATE CONSTRAINT incident_id_unique IF NOT EXISTS
FOR (i:Incident) REQUIRE i.incident_id IS UNIQUE;

// Permits
CREATE CONSTRAINT permit_id_unique IF NOT EXISTS
FOR (p:Permit) REQUIRE p.permit_id IS UNIQUE;

// Rainfall Gauges
CREATE CONSTRAINT rainfall_gauge_id_unique IF NOT EXISTS
FOR (r:RainfallGauge) REQUIRE r.gauge_id IS UNIQUE;

// Locations (catchments, rivers, treatment plants)
CREATE CONSTRAINT location_id_unique IF NOT EXISTS
FOR (l:Location) REQUIRE l.location_id IS UNIQUE;

// ============================================================================
// INDEXES (Optimize query performance)
// ============================================================================

// Spatial queries
CREATE POINT INDEX station_location IF NOT EXISTS
FOR (s:MonitoringStation) ON (s.location);

CREATE POINT INDEX permit_location IF NOT EXISTS
FOR (p:Permit) ON (p.location);

// Temporal queries
CREATE INDEX incident_timestamp IF NOT EXISTS
FOR (i:Incident) ON (i.timestamp);

CREATE INDEX reading_timestamp IF NOT EXISTS
FOR (r:Reading) ON (r.timestamp);

CREATE INDEX discharge_timestamp IF NOT EXISTS
FOR (d:Discharge) ON (d.timestamp);

// Lookup by name/operator
CREATE INDEX permit_operator IF NOT EXISTS
FOR (p:Permit) ON (p.operator);

CREATE INDEX location_name IF NOT EXISTS
FOR (l:Location) ON (l.name);

// Priority filtering
CREATE INDEX incident_priority IF NOT EXISTS
FOR (i:Incident) ON (i.priority);

// ============================================================================
// SAMPLE DATA VERIFICATION QUERIES
// ============================================================================

// After data import, run these to verify:

// 1. Count nodes by type
// MATCH (n) RETURN labels(n) as type, count(*) as count ORDER BY count DESC;

// 2. Find incidents with upstream permits (2 hops)
// MATCH (i:Incident)-[:HAS_READING]->(:Reading)-[:AT_STATION]->(station:MonitoringStation)
// MATCH path = (permit:Permit)-[:DISCHARGES_TO]->(:Location)-[:FLOWS_TO]->(station)
// RETURN i.incident_id, permit.operator, length(path) as hops LIMIT 5;

// 3. Spatial queries (stations within 10km of a point)
// MATCH (s:MonitoringStation)
// WHERE point.distance(s.location, point({latitude: 51.0, longitude: -2.5})) < 10000
// RETURN s.station_id, s.lat, s.lon LIMIT 10;

// 4. Temporal queries (recent incidents)
// MATCH (i:Incident)
// WHERE i.timestamp > datetime() - duration('P7D')
// RETURN i.incident_id, i.timestamp, i.priority
// ORDER BY i.timestamp DESC;
