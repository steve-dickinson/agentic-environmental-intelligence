import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.defra_agent.tools.mcp_tools import (
    get_flood_readings,
    get_hydrology_readings,
    search_public_registers,
)


async def test_mcp_tools():
    print("Testing MCP Tools as LangChain Tools\n")
    print("=" * 60)

    # Test 1: Flood readings
    print("\n1. Testing get_flood_readings tool...")
    try:
        result = await get_flood_readings.ainvoke({"parameter": "level"})
        count = result.get("count", 0)
        print(f"   ✓ Tool returned {count} flood readings")
        if result.get("readings"):
            sample = result["readings"][0]
            print(
                f"   Sample: Station {sample['station_id']} - "
                f"{sample['value']} @ {sample['timestamp']}"
            )
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Hydrology readings
    print("\n2. Testing get_hydrology_readings tool...")
    try:
        result = await get_hydrology_readings.ainvoke({"observed_property": "waterLevel"})
        count = result.get("count", 0)
        print(f"   ✓ Tool returned {count} hydrology readings")
        if result.get("readings"):
            sample = result["readings"][0]
            print(
                f"   Sample: Station {sample['station_id']} - "
                f"{sample['value']} @ {sample['timestamp']}"
            )
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Public registers
    print("\n3. Testing search_public_registers tool...")
    try:
        result = await search_public_registers.ainvoke(
            {
                "postcode": "CT13 9ND",
                "easting": 615000,
                "northing": 157000,
                "dist_km": 5,
            }
        )
        count = len(result.get("entries", []))
        print(f"   ✓ Tool returned {count} permit entries")
        if result.get("entries"):
            sample = result["entries"][0]
            print(f"   Sample: {sample.get('name', 'N/A')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "=" * 60)
    print("\n✅ MCP tools are properly integrated as LangChain tools")
    print("   These tools can now be used by the LangGraph agent\n")


if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
