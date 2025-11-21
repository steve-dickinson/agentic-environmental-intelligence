from datetime import datetime
from typing import Any

import httpx

from defra_agent.domain.models import Reading
from defra_agent.storage.station_repo import StationMetadataRepository

FLOOD_ROOT_URL = "https://environment.data.gov.uk/flood-monitoring"


class FloodClient:
    def __init__(self) -> None:
        self._station_repo = StationMetadataRepository()

    async def get_latest_readings(
        self, parameter: str = "level"
    ) -> list[Reading]:
        url = f"{FLOOD_ROOT_URL}/data/readings"
        params = {"latest": "", "parameter": parameter}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    break
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                if attempt == max_retries - 1:
                    print(f"Failed to fetch flood readings after {max_retries} attempts: {e}")
                    return []
                print(f"Attempt {attempt + 1} failed, retrying...")
                await __import__('asyncio').sleep(2 ** attempt)
        else:
            return []

        raw_items = data.get("items", [])

        station_ids: set[str] = set()
        for item in raw_items:
            measure_url = item.get("measure", "")
            if measure_url:
                # Extract measure ID from URL (last part)
                measure_id = measure_url.split("/")[-1]
                # Station ID is the part before the first hyphen
                parts = measure_id.split("-")
                if parts:
                    station_ids.add(parts[0])

        readings: list[Reading] = []
        for item in raw_items:
            value = item.get("value")
            timestamp = item.get("dateTime")
            measure_url = item.get("measure", "")

            if value is None or timestamp is None or not measure_url:
                continue

            measure_id = measure_url.split("/")[-1]
            station_id = measure_id.split("-")[0]

            meta = self._station_repo.get_station("flood", str(station_id)) or {}
            easting = meta.get("easting")
            northing = meta.get("northing")
            lat = meta.get("lat")
            lon = meta.get("lon")

            readings.append(
                Reading(
                    station_id=station_id,
                    value=float(value),
                    timestamp=datetime.fromisoformat(str(timestamp)),
                    source="flood",
                    easting=int(easting) if easting is not None else None,
                    northing=int(northing) if northing is not None else None,
                    lat=float(lat) if lat is not None else None,
                    lon=float(lon) if lon is not None else None,
                ),
            )

        return readings
