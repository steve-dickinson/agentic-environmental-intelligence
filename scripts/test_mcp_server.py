import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_servers"))

from ea_env_server import get_flood_readings, get_hydrology_readings, search_public_registers
from pydantic import BaseModel


class FloodReadingsInput(BaseModel):
    parameter: str = "level"


class HydrologyReadingsInput(BaseModel):
    observed_property: str = "waterLevel"


class PublicRegisterSearchInput(BaseModel):
    postcode: str
    easting: int
    northing: int
    dist_km: int = 1


async def test_flood_readings() -> None:
    """Test flood readings tool."""
    print("\n" + "=" * 80)
    print("Testing: get_flood_readings")
    print("=" * 80)

    args = FloodReadingsInput(parameter="level")
    result = await get_flood_readings(args)

    print(f"\n✓ Fetched {result['count']} flood readings")

    if result["readings"]:
        print("\nFirst 5 readings:")
        for i, reading in enumerate(result["readings"][:5], 1):
            print(f"\n{i}. Station ID: {reading['station_id']}")
            print(f"   Value: {reading['value']}")
            print(f"   Timestamp: {reading['timestamp']}")
            print(f"   Source: {reading['source']}")
    else:
        print("\n⚠ No readings returned")


async def test_hydrology_readings() -> None:
    """Test hydrology readings tool."""
    print("\n" + "=" * 80)
    print("Testing: get_hydrology_readings")
    print("=" * 80)

    args = HydrologyReadingsInput(observed_property="waterLevel")
    result = await get_hydrology_readings(args)

    print(f"\n✓ Fetched {result['count']} hydrology readings")

    if result["readings"]:
        print("\nFirst 5 readings:")
        for i, reading in enumerate(result["readings"][:5], 1):
            print(f"\n{i}. Station ID: {reading['station_id']}")
            print(f"   Value: {reading['value']}")
            print(f"   Timestamp: {reading['timestamp']}")
            print(f"   Source: {reading['source']}")
    else:
        print("\n⚠ No readings returned")


async def test_public_registers() -> None:
    """Test public registers search tool."""
    print("\n" + "=" * 80)
    print("Testing: search_public_registers")
    print("=" * 80)

    # Use a known test location: CT13 9ND (Discovery Park, Sandwich)
    args = PublicRegisterSearchInput(
        postcode="CT13 9ND", easting=633430, northing=159464, dist_km=2
    )
    result = await search_public_registers(args)

    entries = result.get("entries", [])
    print(f"\n✓ Found {len(entries)} permit entries")

    if entries:
        print("\nFirst 3 permits:")
        for i, entry in enumerate(entries[:3], 1):
            print(f"\n{i}. Operator: {entry.get('holder.name', 'Unknown')}")
            print(f"   Type: {entry.get('registrationType.label', 'N/A')}")
            print(f"   Register: {entry.get('register.label', 'N/A')}")
            print(f"   Address: {entry.get('site.siteAddress.address', 'N/A')}")
            print(f"   Distance: {entry.get('distance', 'N/A')} km")
    else:
        print("\n⚠ No permits returned")


async def main() -> None:
    """Run all MCP server tool tests."""
    print("\n" + "=" * 80)
    print("MCP SERVER TOOL TESTS")
    print("=" * 80)

    try:
        await test_flood_readings()
    except Exception as e:
        print(f"\n✗ Error testing flood readings: {e}")
        import traceback

        traceback.print_exc()

    try:
        await test_hydrology_readings()
    except Exception as e:
        print(f"\n✗ Error testing hydrology readings: {e}")
        import traceback

        traceback.print_exc()

    try:
        await test_public_registers()
    except Exception as e:
        print(f"\n✗ Error testing public registers: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
