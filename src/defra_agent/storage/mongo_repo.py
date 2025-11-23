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

    def get_all_incidents(self, limit: int = 10) -> list[Incident]:
        """Retrieve recent incidents from MongoDB.

        Args:
            limit: Maximum number of incidents to return

        Returns:
            List of Incident objects, most recent first
        """
        from datetime import datetime

        docs = self._collection.find().sort("_id", -1).limit(limit)

        incidents = []
        for doc in docs:
            # Reconstruct Reading objects
            readings = [
                Reading(
                    station_id=r["station_id"],
                    value=r["value"],
                    source=r.get("source", "unknown"),
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    easting=r.get("easting"),
                    northing=r.get("northing"),
                    lat=r.get("lat"),
                    lon=r.get("lon"),
                )
                for r in doc.get("readings", [])
            ]

            # Reconstruct Alert objects
            alerts = [
                Alert(
                    summary=a["summary"],
                    priority=a["priority"],
                    suggested_actions=a.get("suggested_actions", []),
                )
                for a in doc.get("alerts", [])
            ]

            # Reconstruct Permit objects
            permits = [
                Permit(
                    permit_id=p["permit_id"],
                    operator_name=p["operator_name"],
                    register_label=p.get("register_label"),
                    registration_type=p.get("registration_type"),
                    site_address=p.get("site_address", ""),
                    site_postcode=p.get("site_postcode"),
                    distance_km=p.get("distance_km"),
                )
                for p in doc.get("permits", [])
            ]

            incidents.append(
                Incident(
                    id=doc["_id"],
                    readings=readings,
                    alerts=alerts,
                    permits=permits,
                )
            )

        return incidents
