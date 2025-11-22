import asyncio

from defra_agent.tools.hydrology_client import HydrologyClient


async def main() -> None:
    client = HydrologyClient()

    print("Fetching latest hydrology readings...")
    try:
        readings = await client.get_latest_readings()

        print(f"\n✓ Successfully fetched {len(readings)} hydrology readings")

        if readings:
            print("\nFirst 5 readings:")
            for i, reading in enumerate(readings[:5], 1):
                print(
                    f"{i}. Station: {reading.station_id}, Value: {reading.value}, "
                    f"Time: {reading.timestamp}, Source: {reading.source}"
                )
                if reading.lat and reading.lon:
                    print(f"   Location: ({reading.lat}, {reading.lon})")
        else:
            print("\n⚠ No readings returned - this might be normal if the API has no current data")

    except Exception as e:
        print(f"\n✗ Error fetching hydrology readings: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
