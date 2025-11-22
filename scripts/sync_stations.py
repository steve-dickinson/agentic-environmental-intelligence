from __future__ import annotations

import asyncio
from typing import Any

import httpx

from defra_agent.storage.station_repo import StationMetadataRepository

FLOOD_STATIONS_URL = "https://environment.data.gov.uk/flood-monitoring/id/stations"
HYDRO_STATIONS_URL = "https://environment.data.gov.uk/hydrology/id/stations"
RAINFALL_STATIONS_URL = (
    "https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=rainfall"
)


async def _fetch_all(url: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    params = {"_limit": 1000}  # Increased limit to fetch more stations
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("items", [])
            items.extend(batch)

            next_link = None
            for link in data.get("links", []):
                if link.get("rel") == "next":
                    next_link = link.get("href")
                    break
            if not next_link:
                break
            url = next_link
            params = {}
    return items


async def main() -> None:
    repo = StationMetadataRepository()

    print("Fetching all flood-monitoring stations (includes rainfall)...")
    flood_items = await _fetch_all(FLOOD_STATIONS_URL)
    repo.bulk_upsert("flood", flood_items)
    print(f"Stored {len(flood_items)} flood stations")

    rainfall_stations = [
        s
        for s in flood_items
        if any(m.get("parameter") == "rainfall" for m in s.get("measures", []))
    ]
    repo.bulk_upsert("rainfall", rainfall_stations)
    print(f"Stored {len(rainfall_stations)} rainfall stations (subset of flood stations)")

    print("Fetching all hydrology stations...")
    hydro_items = await _fetch_all(HYDRO_STATIONS_URL)
    repo.bulk_upsert("hydrology", hydro_items)
    print(f"Stored {len(hydro_items)} hydrology stations")


if __name__ == "__main__":
    asyncio.run(main())
