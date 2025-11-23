"""Repository for storing agent execution run logs in MongoDB."""

from datetime import datetime

from pymongo import MongoClient

from defra_agent.config import settings
from defra_agent.domain.models import AgentRunLog


class RunLogRepository:
    """Store and retrieve agent execution logs."""

    def __init__(self) -> None:
        self.client = MongoClient(settings.mongo_uri)
        self.db = self.client[settings.mongo_db]
        self.collection = self.db["agent_run_logs"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient querying."""
        self.collection.create_index("run_id", unique=True)
        self.collection.create_index([("timestamp", -1)])  # Most recent first
        self.collection.create_index("incidents_created")

    def save_run_log(self, log: AgentRunLog) -> None:
        """Save an agent run log to MongoDB."""
        doc = {
            "run_id": log.run_id,
            "timestamp": log.timestamp,
            
            # Data collection
            "stations_fetched": log.stations_fetched,
            "readings_fetched": log.readings_fetched,
            "flood_warnings_fetched": log.flood_warnings_fetched,
            
            # Clustering
            "clusters_found": log.clusters_found,
            "cluster_details": [
                {
                    "type": c.type,
                    "station_count": c.station_count,
                    "station_ids": c.station_ids,
                    "center_lat": c.center_lat,
                    "center_lon": c.center_lon,
                }
                for c in log.cluster_details
            ],
            
            # RAG enrichment
            "rag_searches_performed": log.rag_searches_performed,
            "rag_results": [
                {
                    "similar_incidents_found": r.similar_incidents_found,
                    "avg_similarity": r.avg_similarity,
                    "best_similarity": r.best_similarity,
                    "similar_incident_ids": r.similar_incident_ids,
                }
                for r in log.rag_results
            ],
            
            # Incident creation
            "incidents_created": log.incidents_created,
            "incidents_duplicate": log.incidents_duplicate,
            "incident_ids_created": log.incident_ids_created,
            "incident_ids_duplicate": log.incident_ids_duplicate,
            
            # Storage
            "mongodb_stored": log.mongodb_stored,
            "pgvector_stored": log.pgvector_stored,
            "neo4j_stored": log.neo4j_stored,
            
            # Performance
            "duration_seconds": log.duration_seconds,
            "errors": log.errors,
            "openai_api_calls": log.openai_api_calls,
        }
        
        self.collection.update_one(
            {"run_id": log.run_id},
            {"$set": doc},
            upsert=True,
        )

    def get_recent_runs(self, limit: int = 10) -> list[dict]:
        """Get the most recent agent runs."""
        cursor = self.collection.find().sort("timestamp", -1).limit(limit)
        return list(cursor)

    def get_run_by_id(self, run_id: str) -> dict | None:
        """Get a specific run log by ID."""
        return self.collection.find_one({"run_id": run_id})

    def get_statistics(self, days: int = 7) -> dict:
        """Get aggregate statistics over the last N days."""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {
                "$group": {
                    "_id": None,
                    "total_runs": {"$sum": 1},
                    "total_incidents_created": {"$sum": "$incidents_created"},
                    "total_incidents_duplicate": {"$sum": "$incidents_duplicate"},
                    "total_clusters": {"$sum": "$clusters_found"},
                    "avg_duration": {"$avg": "$duration_seconds"},
                    "total_rag_searches": {"$sum": "$rag_searches_performed"},
                }
            },
        ]
        
        result = list(self.collection.aggregate(pipeline))
        
        if not result:
            return {
                "total_runs": 0,
                "total_incidents_created": 0,
                "total_incidents_duplicate": 0,
                "total_clusters": 0,
                "avg_duration": 0,
                "total_rag_searches": 0,
                "duplicate_rate": 0,
            }
        
        stats = result[0]
        total_created = stats["total_incidents_created"]
        total_dup = stats["total_incidents_duplicate"]
        total = total_created + total_dup
        
        return {
            "total_runs": stats["total_runs"],
            "total_incidents_created": total_created,
            "total_incidents_duplicate": total_dup,
            "total_clusters": stats["total_clusters"],
            "avg_duration": round(stats["avg_duration"], 2),
            "total_rag_searches": stats["total_rag_searches"],
            "duplicate_rate": round(total_dup / total * 100, 1) if total > 0 else 0,
        }

    def close(self) -> None:
        """Close the MongoDB connection."""
        self.client.close()
