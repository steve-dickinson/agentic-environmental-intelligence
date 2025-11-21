import asyncio
import logging
from datetime import datetime

import httpx

from defra_agent.domain.models import Reading

FLOOD_ROOT_URL = "https://environment.data.gov.uk/flood-monitoring"

logger = logging.getLogger(__name__)


class FloodClient:
    """HTTP client for EA Flood Monitoring API."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0) -> None:
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def get_latest_readings(self, parameter: str = "level") -> list[Reading]:
        """Fetch latest readings and convert them into domain Reading objects.

        Retries on failure with exponential backoff.
        """
        url = f"{FLOOD_ROOT_URL}/data/readings"
        params = {"latest": "", "parameter": parameter}

        timeout = httpx.Timeout(60.0, connect=10.0)

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
            station = item.get("stationReference")
            if station is None:
                measure = item.get("measure")
                if isinstance(measure, dict):
                    station = measure.get("@id")
                elif isinstance(measure, str):
                    station = measure
            timestamp = item.get("dateTime")

            if value is None or station is None or timestamp is None:
                continue

            readings.append(
                Reading(
                    station_id=str(station),
                    value=float(value),
                    timestamp=datetime.fromisoformat(str(timestamp)),
                    source="flood",
                ),
            )

        return readings
