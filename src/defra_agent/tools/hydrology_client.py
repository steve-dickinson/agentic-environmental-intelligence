from datetime import datetime

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
                await __import__("asyncio").sleep(2**attempt)
        else:
            return []

        raw_items = data.get("items", [])

        station_ids: set[str] = set()
        for item in raw_items:
            measure = item.get("measure", "")

            if isinstance(measure, dict):
                measure_url = measure.get("@id", "")
            else:
                measure_url = str(measure) if measure else ""

            if measure_url:
                measure_id = measure_url.split("/")[-1]

                parts = measure_id.split("-")
                if parts:
                    station_ids.add(parts[0])

        readings: list[Reading] = []
        for item in raw_items:
            value = item.get("value")
            timestamp = item.get("dateTime")
            measure = item.get("measure", "")

            if isinstance(measure, dict):
                measure_url = measure.get("@id", "")
            else:
                measure_url = str(measure) if measure else ""

            if value is None or timestamp is None or not measure_url:
                continue

            measure_id = measure_url.split("/")[-1]
            station_id = measure_id.split("-")[0]

            meta = self._station_repo.get_station("hydrology", str(station_id)) or {}
            easting = meta.get("easting")
            northing = meta.get("northing")
            lat = meta.get("lat")
            lon = meta.get("lon")

            readings.append(
                Reading(
                    station_id=station_id,
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
