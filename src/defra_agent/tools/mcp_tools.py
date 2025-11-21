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
        - measure_url: URL to the measure
    """
    readings_url = "https://environment.data.gov.uk/flood-monitoring/data/readings"
    readings_params = {
        "latest": "",
        "parameter": parameter,
    }
    readings_json = await _get_json(readings_url, readings_params)
    raw_items = readings_json.get("items", [])

    enriched_readings: list[dict[str, Any]] = []
    for item in raw_items:
        value = item.get("value")
        timestamp = item.get("dateTime")
        measure_url = item.get("measure", "")

        if value is None or timestamp is None or not measure_url:
            continue

        station_id = _extract_station_id_from_measure(measure_url)
        if not station_id:
            continue

        enriched_readings.append(
            {
                "station_id": station_id,
                "value": float(value),
                "timestamp": str(timestamp),
                "source": "flood",
                "measure_url": str(measure_url),
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
        - measure_url: URL to the measure
    """
    readings_url = "https://environment.data.gov.uk/hydrology/data/readings.json"
    readings_params = {
        "latest": "",
        "observedProperty": observed_property,
    }
    readings_json = await _get_json(readings_url, readings_params)
    raw_items = readings_json.get("items", [])

    enriched_readings: list[dict[str, Any]] = []
    for item in raw_items:
        value = item.get("value")
        timestamp = item.get("dateTime")
        measure = item.get("measure", "")

        if value is None or timestamp is None or not measure:
            continue

        station_id = _extract_station_id_from_measure(measure)
        if not station_id:
            continue

        if isinstance(measure, dict):
            measure_url = measure.get("@id", "")
        else:
            measure_url = str(measure)

        enriched_readings.append(
            {
                "station_id": station_id,
                "value": float(value),
                "timestamp": str(timestamp),
                "source": "hydrology",
                "measure_url": measure_url,
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
