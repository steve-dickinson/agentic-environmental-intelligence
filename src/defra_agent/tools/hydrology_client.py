from datetime import datetime
from typing import Any

import httpx

from defra_agent.domain.models import Reading
from defra_agent.storage.station_repo import StationMetadataRepository

HYDROLOGY_ROOT_URL = "https://environment.data.gov.uk/hydrology"


class HydrologyClient:
    def __init__(self) -> None:
        self._station_repo = StationMetadataRepository()

    async def get_latest_readings(self, observed_property: str = "waterLevel") -> list[Reading]:
        url = f"{HYDROLOGY_ROOT_URL}/data/readings.json"
        params = {"latest": "", "observedProperty": observed_property}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    break
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                if attempt == max_retries - 1:
                    print(f"Failed to fetch hydrology readings after {max_retries} attempts: {e}")
                    return []
                print(f"Attempt {attempt + 1} failed, retrying...")
                await __import__('asyncio').sleep(2 ** attempt)
        else:
            return []

        raw_items = data.get("items", [])

        station_ids: set[str] = set()
        for item in raw_items:
            station = item.get("stationReference") or item.get("stationGuid")
            if station:
                station_ids.add(str(station))

        readings: list[Reading] = []
        for item in raw_items:
            value = item.get("value")
            station = item.get("stationReference") or item.get("stationGuid")
            timestamp = item.get("dateTime")

            if value is None or station is None or timestamp is None:
                continue

            meta = self._station_repo.get_station("hydrology", str(station)) or {}
            easting = meta.get("easting")
            northing = meta.get("northing")
            lat = meta.get("lat")
            lon = meta.get("lon")

            readings.append(
                Reading(
                    station_id=str(station),
                    value=float(value),
                    timestamp=datetime.fromisoformat(str(timestamp)),
                    source="hydrology",
                    easting=int(easting) if easting is not None else None,
                    northing=int(northing) if northing is not None else None,
                    lat=float(lat) if lat is not None else None,
                    lon=float(lon) if lon is not None else None,
                ),
            )

        return readings
