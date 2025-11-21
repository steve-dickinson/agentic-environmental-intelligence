import asyncio
import logging
from datetime import datetime

import httpx

from defra_agent.domain.models import Reading

HYDROLOGY_ROOT_URL = "https://environment.data.gov.uk/hydrology"

logger = logging.getLogger(__name__)


class HydrologyClient:
    """HTTP client for EA Hydrology API (flows, groundwater, etc.)."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0) -> None:
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def get_latest_readings(self, parameter: str = "flow") -> list[Reading]:
        """
        Fetch latest hydrology readings and convert them into domain Reading objects.

        The EA hydrology API supports similar patterns to the flood monitoring API,
        e.g. /data/readings?latest&parameter=flow

        Retries on failure with exponential backoff.
        """
        url = f"{HYDROLOGY_ROOT_URL}/data/readings.json"
        params = {"latest": "", "parameter": parameter}

        timeout = httpx.Timeout(60.0, connect=10.0)

        print(f"Fetching hydrology readings from {url} with params {params}")

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                break

            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed for {url}. " f"Last error: {e}"
                    )
                    raise

        readings: list[Reading] = []

        for item in data.get("items", []):
            value = item.get("value")
            station = item.get("stationReference") or item.get("measure", {}).get("@id")
            timestamp = item.get("dateTime")

            if value is None or station is None or timestamp is None:
                continue

            readings.append(
                Reading(
                    station_id=str(station),
                    value=float(value),
                    timestamp=datetime.fromisoformat(str(timestamp)),
                    source="hydrology",
                ),
            )

        return readings
