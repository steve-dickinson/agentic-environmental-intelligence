from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo import MongoClient, UpdateOne

from defra_agent.config import settings


class StationMetadataRepository:

    def __init__(self) -> None:
        client = MongoClient(settings.mongo_uri)
        db = client[settings.mongo_db]
        self._collection = db["station_metadata"]
        self._collection.create_index("station_id")
        self._collection.create_index("source")

    @staticmethod
    def _doc_id(source: str, station_id: str) -> str:
        return f"{source}:{station_id}"

    def upsert_station(
        self,
        source: str,
        station_id: str,
        lat: float | None,
        lon: float | None,
        easting: int | None,
        northing: int | None,
        label: str | None = None,
    ) -> None:
        doc_id = self._doc_id(source, station_id)
        update = {
            "$set": {
                "source": source,
                "station_id": station_id,
                "lat": lat,
                "lon": lon,
                "easting": easting,
                "northing": northing,
                "label": label,
                "last_seen": datetime.utcnow().isoformat(),
            },
        }
        self._collection.update_one({"_id": doc_id}, update, upsert=True)

    def bulk_upsert(self, source: str, stations: list[dict[str, Any]]) -> None:
        ops: list[UpdateOne] = []
        now = datetime.utcnow().isoformat()

        for s in stations:
            station_id = s.get("stationReference") or s.get("stationGuid")
            if not station_id:
                continue
            lat = s.get("lat")
            lon = s.get("long")
            easting = s.get("easting")
            northing = s.get("northing")
            label = s.get("label")

            doc_id = self._doc_id(source, station_id)
            ops.append(
                UpdateOne(
                    {"_id": doc_id},
                    {
                        "$set": {
                            "source": source,
                            "station_id": station_id,
                            "lat": lat,
                            "lon": lon,
                            "easting": easting,
                            "northing": northing,
                            "label": label,
                            "last_seen": now,
                        },
                    },
                    upsert=True,
                ),
            )

        if ops:
            self._collection.bulk_write(ops)

    def get_station(self, source: str, station_id: str) -> dict[str, Any] | None:
        doc_id = self._doc_id(source, station_id)
        return self._collection.find_one({"_id": doc_id})
