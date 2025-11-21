from typing import Any
from uuid import uuid4

from pymongo import MongoClient

from defra_agent.config import settings
from defra_agent.domain.models import Alert, Incident, Reading


class IncidentRepository:
    """Persistence for incidents in MongoDB."""

    def __init__(self) -> None:
        self._client: MongoClient[dict[str, Any]] = MongoClient(settings.mongo_uri)
        self._db = self._client[settings.mongo_db]
        self._collection = self._db["incidents"]

    def create_incident(self, readings: list[Reading], alerts: list[Alert]) -> Incident:
        incident_id = str(uuid4())
        doc = {
            "_id": incident_id,
            "readings": [
                {
                    "station_id": r.station_id,
                    "value": r.value,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in readings
            ],
            "alerts": [
                {
                    "summary": a.summary,
                    "priority": a.priority.value,
                    "suggested_actions": a.suggested_actions,
                }
                for a in alerts
            ],
        }
        self._collection.insert_one(doc)

        return Incident(id=incident_id, readings=readings, alerts=alerts)
