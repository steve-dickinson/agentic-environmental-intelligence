#!/usr/bin/env python3
"""Debug rainfall client station lookup."""

import asyncio

import httpx

from defra_agent.storage.station_repo import StationMetadataRepository


async def main() -> None:
    # Fetch first rainfall reading
    url = "https://environment.data.gov.uk/flood-monitoring/data/readings"
    params = {"latest": "", "parameter": "rainfall", "_limit": 5}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        data = resp.json()

    items = data.get("items", [])
    print(f"Fetched {len(items)} readings from API\n")

    repo = StationMetadataRepository()

    for item in items:
        measure_url = item.get("measure", "")
        station_id = measure_url.split("/")[-1].split("-")[0] if measure_url else None

        print(f"Reading: {measure_url}")
        print(f"  Extracted station_id: {station_id}")

        if station_id:
            # Try rainfall
            metadata_rainfall = repo.get_station("rainfall", station_id)
            print(f"  Metadata (rainfall source): {metadata_rainfall is not None}")
            if metadata_rainfall:
                print(
                    f"    lat/lon: {metadata_rainfall.get('lat')}, {metadata_rainfall.get('lon')}"
                )

            # Try flood
            metadata_flood = repo.get_station("flood", station_id)
            print(f"  Metadata (flood source): {metadata_flood is not None}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
