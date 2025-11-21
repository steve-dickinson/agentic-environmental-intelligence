import asyncio

from defra_agent.tools.flood_client import FloodClient


async def _run_once() -> None:
    client = FloodClient()
    readings = await client.get_latest_readings()
    assert isinstance(readings, list)


def test_flood_client_returns_list() -> None:
    asyncio.run(_run_once())
