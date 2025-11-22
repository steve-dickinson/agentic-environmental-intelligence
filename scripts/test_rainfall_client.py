#!/usr/bin/env python3
"""Test the rainfall client."""

import asyncio

from defra_agent.tools.rainfall_client import RainfallClient


async def main() -> None:
    client = RainfallClient()

    print("Fetching latest rainfall readings...")
    readings = await client.get_latest_readings()
    print(f"Total readings: {len(readings)}")

    # Show first 5 with coordinates
    with_coords = [r for r in readings if r.lat is not None and r.lon is not None]
    print(f"Readings with coordinates: {len(with_coords)}")

    if with_coords:
        print("\nFirst 5 rainfall readings with coordinates:")
        for r in with_coords[:5]:
            print(f"  {r.station_id}: {r.value}mm at ({r.lat:.4f}, {r.lon:.4f}) - {r.timestamp}")

    # Test spatial search around London
    print("\n\nTesting rainfall near London (51.5, -0.1)...")
    nearby = await client.get_rainfall_near_location(lat=51.5, lon=-0.1, radius_km=20, hours=24)
    print(f"Found {len(nearby)} rainfall stations within 20km")

    if nearby:
        stats = await client.calculate_total_rainfall(lat=51.5, lon=-0.1, radius_km=20, hours=24)
        print(f"Total rainfall: {stats['total_mm']:.1f}mm")
        print(f"Max rainfall: {stats['max_mm']:.1f}mm")
        print(f"Station count: {stats['station_count']}")


if __name__ == "__main__":
    asyncio.run(main())
