from __future__ import annotations

import csv
import io
from typing import Any

import httpx
from langchain_core.tools import tool


def _extract_station_id_from_measure(measure: Any) -> str | None:
    measure_url = ""
    if isinstance(measure, dict):
        measure_url = measure.get("@id", "")
    elif isinstance(measure, str):
        measure_url = measure

    if not measure_url:
        return None

    measure_id = measure_url.split("/")[-1]
    parts = measure_id.split("-")
    return parts[0] if parts else None


async def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch JSON with retry logic for slow EA APIs."""
    max_retries = 2
    timeout = 60.0  # Increased timeout for slow EA APIs

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except (httpx.TimeoutException, httpx.ReadTimeout) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"API timeout after {max_retries} attempts: {url}") from e
            # Retry once
            continue
    return {}


async def _get_text(url: str, params: dict[str, Any] | None = None) -> str:
    """Fetch text with retry logic."""
    max_retries = 2
    timeout = 60.0

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.text
        except (httpx.TimeoutException, httpx.ReadTimeout) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"API timeout after {max_retries} attempts: {url}") from e
            continue
    return ""


@tool
async def get_flood_readings(parameter: str = "level") -> dict[str, Any]:
    """Get latest flood monitoring readings from Environment Agency.

    Args:
        parameter: Parameter to filter by (e.g. 'level', 'flow'). Default is 'level'.

    Returns:
        Dictionary with 'readings' list and 'count'. Each reading has:
        - station_id: Station identifier
        - value: Reading value
        - timestamp: When reading was taken
        - source: Always 'flood'
        - easting: British National Grid easting coordinate
        - northing: British National Grid northing coordinate
        - lat: Latitude (WGS84)
        - lon: Longitude (WGS84)
    """
    from defra_agent.tools.flood_client import FloodClient

    client = FloodClient()
    readings = await client.get_latest_readings(parameter=parameter)

    enriched_readings: list[dict[str, Any]] = []
    for reading in readings:
        enriched_readings.append(
            {
                "station_id": reading.station_id,
                "value": reading.value,
                "timestamp": reading.timestamp.isoformat(),
                "source": reading.source,
                "easting": reading.easting,
                "northing": reading.northing,
                "lat": reading.lat,
                "lon": reading.lon,
            }
        )

    return {
        "readings": enriched_readings,
        "count": len(enriched_readings),
    }


@tool
async def get_hydrology_readings(observed_property: str = "waterLevel") -> dict[str, Any]:
    """Get latest hydrology readings from Environment Agency.

    Args:
        observed_property: Property to filter by (e.g. 'waterLevel', 'waterFlow').
                          Default is 'waterLevel'.

    Returns:
        Dictionary with 'readings' list and 'count'. Each reading has:
        - station_id: Station identifier
        - value: Reading value
        - timestamp: When reading was taken
        - source: Always 'hydrology'
        - easting: British National Grid easting coordinate
        - northing: British National Grid northing coordinate
        - lat: Latitude (WGS84)
        - lon: Longitude (WGS84)
    """
    from defra_agent.tools.hydrology_client import HydrologyClient

    client = HydrologyClient()
    readings = await client.get_latest_readings(observed_property=observed_property)

    enriched_readings: list[dict[str, Any]] = []
    for reading in readings:
        enriched_readings.append(
            {
                "station_id": reading.station_id,
                "value": reading.value,
                "timestamp": reading.timestamp.isoformat(),
                "source": reading.source,
                "easting": reading.easting,
                "northing": reading.northing,
                "lat": reading.lat,
                "lon": reading.lon,
            }
        )

    return {
        "readings": enriched_readings,
        "count": len(enriched_readings),
    }


@tool
async def search_public_registers(
    postcode: str,
    easting: int,
    northing: int,
    dist_km: int = 1,
) -> dict[str, Any]:
    """Search Environment Agency Public Registers near a location.

    Args:
        postcode: UK postcode to search around (e.g. 'CT13 9ND')
        easting: OS National Grid easting coordinate
        northing: OS National Grid northing coordinate
        dist_km: Search radius in kilometres (1-10). Default is 1.

    Returns:
        Dictionary with 'entries' list containing permit records and 'meta' info.
        Each entry contains permit details like name, type, status, location.
    """
    base_url = "https://environment.data.gov.uk/public-register/api/search.csv"
    params = {
        "__postcode": postcode,
        "dist": dist_km,
        "easting": easting,
        "northing": northing,
    }

    csv_text = await _get_text(base_url, params)
    csv_file = io.StringIO(csv_text)
    reader = csv.DictReader(csv_file)
    rows = list(reader)

    return {
        "entries": rows,
        "meta": {
            "url": base_url,
            "query": params,
        },
    }
