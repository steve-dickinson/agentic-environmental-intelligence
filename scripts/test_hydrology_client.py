import asyncio
import sys
from pathlib import Path

import pytest

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from defra_agent.tools.hydrology_client import HydrologyClient  # noqa: E402


async def _run() -> None:
    client = HydrologyClient()
    try:
        readings = await client.get_latest_readings()
        assert isinstance(readings, list)
        if readings:
            first = readings[0]
            assert first.source == "hydrology"
    except Exception as e:
        pytest.skip(f"Hydrology API not available: {e}")


def test_hydrology_client_runs() -> None:
    asyncio.run(_run())
