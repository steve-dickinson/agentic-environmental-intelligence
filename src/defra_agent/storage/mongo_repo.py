from typing import Any
from uuid import uuid4

from pymongo import MongoClient

from defra_agent.config import settings
from defra_agent.domain.models import Alert, Incident, Permit, Reading


class IncidentRepository:
    def __init__(self) -> None:
        self._client: MongoClient[dict[str, Any]] = MongoClient(settings.mongo_uri)
        self._db = self._client[settings.mongo_db]
        self._collection = self._db["incidents"]

    def create_incident(
        self,
        readings: list[Reading],
        alerts: list[Alert],
        permits: list[Permit] | None = None,
    ) -> Incident:
        incident_id = str(uuid4())
        doc = {
            "_id": incident_id,
            "readings": [
                {
                    "station_id": r.station_id,
                    "value": r.value,
                    "source": r.source,
                    "timestamp": r.timestamp.isoformat(),
                    "easting": r.easting,
                    "northing": r.northing,
                    "lat": r.lat,
                    "lon": r.lon,
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
            "permits": [
                {
                    "permit_id": p.permit_id,
                    "operator_name": p.operator_name,
                    "register_label": p.register_label,
                    "registration_type": p.registration_type,
                    "site_address": p.site_address,
                    "site_postcode": p.site_postcode,
                    "distance_km": p.distance_km,
                }
                for p in (permits or [])
            ],
        }
        self._collection.insert_one(doc)

        return Incident(
            id=incident_id,
            readings=readings,
            alerts=alerts,
            permits=permits or [],
        )
