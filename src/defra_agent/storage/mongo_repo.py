import hashlib
import json
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
        # Create index on content_hash for duplicate detection
        self._collection.create_index("content_hash", unique=False)

    def _generate_content_hash(self, readings: list[Reading], alerts: list[Alert]) -> str:
        """Generate a deterministic hash from incident content for deduplication.
        
        Uses station IDs, timestamps, and alert summaries to identify duplicates.
        """
        # Create a canonical representation
        content = {
            "stations": sorted(set(r.station_id for r in readings)),
            "timestamps": sorted(set(r.timestamp.isoformat() for r in readings)),
            "alert_summaries": sorted(a.summary for a in alerts),
        }
        
        # Generate hash
        content_json = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_json.encode()).hexdigest()[:16]

    def create_incident(
        self,
        readings: list[Reading],
        alerts: list[Alert],
        permits: list[Permit] | None = None,
    ) -> Incident:
        """Create an incident, avoiding duplicates based on content hash.
        
        Returns existing incident if duplicate detected, otherwise creates new.
        """
        # Generate content hash for deduplication
        content_hash = self._generate_content_hash(readings, alerts)
        
        # Check if incident with same content already exists (within last 24 hours)
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=1)
        
        existing = self._collection.find_one({
            "content_hash": content_hash,
            "_id": {"$gt": cutoff.isoformat()[:10]}  # Rough filter by date in UUID
        })
        
        if existing:
            # Return existing incident
            print(f"   ℹ️  Duplicate incident detected (hash: {content_hash[:8]}...) - skipping")
            return Incident(
                id=existing["_id"],
                readings=readings,
                alerts=alerts,
                permits=permits or [],
            )
        
        incident_id = str(uuid4())
        doc = {
            "content_hash": content_hash,
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
