from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from defra_agent.domain.models import Reading
from defra_agent.storage.station_repo import StationMetadataRepository

FLOOD_API_BASE = "https://environment.data.gov.uk/flood-monitoring"


class RainfallClient:
    """Client for Environment Agency rainfall readings."""

    def __init__(self) -> None:
        """Initialize rainfall client with station metadata repository."""
        self.station_repo = StationMetadataRepository()
        self._metadata_cache: dict[str, dict[str, Any] | None] = {}

    def _extract_station_id(self, measure_url: str) -> str | None:
        """Extract station ID from measure URL."""
        if not measure_url:
            return None
        measure_id = measure_url.split("/")[-1]
        parts = measure_id.split("-")
        return parts[0] if parts else None

    async def _fetch_station_metadata(self, station_id: str) -> dict[str, Any] | None:
        """Fetch station metadata directly from API if not in database (cached)."""
        # Check cache first
        if station_id in self._metadata_cache:
            return self._metadata_cache[station_id]

        url = f"{FLOOD_API_BASE}/id/stations/{station_id}"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:  # Reduced timeout
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                station_data = data.get("items", {})
                metadata = {
                    "lat": station_data.get("lat"),
                    "lon": station_data.get("long"),  # API uses "long"
                    "easting": station_data.get("easting"),
                    "northing": station_data.get("northing"),
                }
                self._metadata_cache[station_id] = metadata
                return metadata
        except Exception:
            # Cache the failure to avoid retrying
            self._metadata_cache[station_id] = None
            return None

    async def get_latest_readings(self, parameter: str = "rainfall") -> list[Reading]:
        """Fetch latest rainfall readings from EA Flood Monitoring API.

        Args:
            parameter: Measurement parameter (default: 'rainfall')

        Returns:
            List of Reading objects with enriched coordinate data
        """
        url = f"{FLOOD_API_BASE}/data/readings"
        params = {"latest": "", "parameter": parameter}

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.TimeoutException, httpx.HTTPError) as e:
                print(f"Error fetching rainfall data: {e}")
                return []

        items = data.get("items", [])

        # Batch-load all station metadata to avoid N database queries
        station_ids = set()
        for item in items:
            measure_url = item.get("measure", "")
            station_id = self._extract_station_id(measure_url)
            if station_id:
                station_ids.add(station_id)

        # Pre-load all station metadata from database
        metadata_map = {}
        for sid in station_ids:
            metadata = self.station_repo.get_station("rainfall", sid)
            if not metadata:
                metadata = self.station_repo.get_station("flood", sid)
            if metadata and metadata.get("lat") and metadata.get("lon"):
                metadata_map[sid] = metadata

        readings: list[Reading] = []

        for item in items:
            value = item.get("value")
            timestamp_str = item.get("dateTime")
            measure_url = item.get("measure", "")

            if value is None or timestamp_str is None:
                continue

            # Handle value being a list (take the first element)
            if isinstance(value, list):
                if not value:
                    continue
                value = value[0]

            station_id = self._extract_station_id(measure_url)
            if not station_id or station_id not in metadata_map:
                continue

            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            # Get coordinates from pre-loaded metadata
            metadata = metadata_map[station_id]
            easting = metadata.get("easting")
            northing = metadata.get("northing")
            lat = metadata.get("lat")
            lon = metadata.get("lon")

            readings.append(
                Reading(
                    station_id=station_id,
                    value=float(value),
                    timestamp=timestamp,
                    source="rainfall",
                    easting=easting,
                    northing=northing,
                    lat=lat,
                    lon=lon,
                )
            )

        return readings

    async def get_rainfall_near_location(
        self, lat: float, lon: float, radius_km: float = 10.0, hours: int = 24
    ) -> list[Reading]:
        """Get rainfall readings near a specific location within a time window.

        Args:
            lat: Latitude of location
            lon: Longitude of location
            radius_km: Search radius in kilometers
            hours: Time window in hours (lookback period)

        Returns:
            List of rainfall readings near the location
        """
        from defra_agent.domain.clustering import _haversine_distance

        # Get all recent readings
        all_readings = await self.get_latest_readings()

        # Filter by location and time
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        nearby_readings = []

        for reading in all_readings:
            # Check if reading has coordinates
            if reading.lat is None or reading.lon is None:
                continue

            # Check distance
            distance = _haversine_distance(lat, lon, reading.lat, reading.lon)
            if distance > radius_km:
                continue

            # Check time
            ts = reading.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts < cutoff_time:
                continue

            nearby_readings.append(reading)

        return nearby_readings

    async def calculate_total_rainfall(
        self, lat: float, lon: float, radius_km: float = 10.0, hours: int = 24
    ) -> dict[str, Any]:
        """Calculate total rainfall statistics for a location.

        Args:
            lat: Latitude of location
            lon: Longitude of location
            radius_km: Search radius in kilometers
            hours: Time window in hours

        Returns:
            Dictionary with rainfall statistics:
            - total_mm: Total rainfall in mm
            - max_mm: Maximum single reading in mm
            - station_count: Number of stations with data
            - readings: List of Reading objects
        """
        readings = await self.get_rainfall_near_location(lat, lon, radius_km, hours)

        if not readings:
            return {
                "total_mm": 0.0,
                "max_mm": 0.0,
                "station_count": 0,
                "readings": [],
            }

        total = sum(r.value for r in readings)
        max_val = max(r.value for r in readings)
        stations = len(set(r.station_id for r in readings))

        return {
            "total_mm": round(total, 2),
            "max_mm": round(max_val, 2),
            "station_count": stations,
            "readings": readings,
        }
