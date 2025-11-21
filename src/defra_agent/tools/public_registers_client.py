import httpx

from defra_agent.config import settings
from defra_agent.domain.models import Permit, Reading


class PublicRegistersClient:
    """
    Client for Environment Agency Public Registers (permits).
    """

    def __init__(self) -> None:
        self._base_url = settings.public_registers_base_url.rstrip("/")

    async def search_permits_by_station(self, reading: Reading) -> list[Permit]:
        """
        Find permits that are potentially related to a given reading.

        For this POC, we assume we can search by station id (or by location if you adapt it).
        Replace query parameter names with the actual public registers API expectations.
        """

        url = f"{self._base_url}/search"
        params = {"term": reading.station_id}

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        permits: list[Permit] = []

        # This assumes an "items" list with typical fields.
        # Adjust key names to match the real API shape.
        for item in data.get("items", []):
            permit_id = item.get("permitId") or item.get("id") or ""
            operator = item.get("operatorName") or item.get("operator") or "Unknown operator"
            activity = item.get("activity") or item.get("activityType")
            location = item.get("location") or item.get("siteName")

            easting = item.get("easting")
            northing = item.get("northing")

            permits.append(
                Permit(
                    permit_id=str(permit_id),
                    operator_name=str(operator),
                    activity=str(activity) if activity is not None else None,
                    location=str(location) if location is not None else None,
                    easting=float(easting) if easting is not None else None,
                    northing=float(northing) if northing is not None else None,
                ),
            )

        return permits
