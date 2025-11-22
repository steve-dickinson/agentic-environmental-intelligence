import asyncio
import csv
import io
import logging
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("ea-environment")


async def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    logger.debug("GET %s params=%s", url, params)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def _get_text(url: str, params: dict[str, Any] | None = None) -> str:
    logger.debug("GET %s params=%s", url, params)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.text


def _extract_station_id_from_measure(measure: Any) -> str | None:
    """Extract station ID from measure URL or dict."""
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


class FloodReadingsInput(BaseModel):
    parameter: str = Field(
        "level",
        description="Parameter to filter readings by (e.g. 'level', 'flow').",
    )


@mcp.tool(description="Get latest flood-monitoring readings with station metadata.")
async def get_flood_readings(args: FloodReadingsInput) -> dict[str, Any]:
    """
    Fetches latest flood readings with basic parsing of station IDs.

    Returns:
      {
        "readings": [
          {
            "station_id": "...",
            "value": 1.23,
            "timestamp": "2025-11-21T12:00:00",
            "source": "flood",
            "measure_url": "..."
          }
        ],
        "count": 100
      }
    """
    # Fetch all latest readings
    readings_url = "https://environment.data.gov.uk/flood-monitoring/data/readings"
    readings_params = {
        "latest": "",
        "parameter": args.parameter,
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


class HydrologyReadingsInput(BaseModel):
    observed_property: str = Field(
        "waterLevel",
        description="Hydrology observedProperty (e.g. 'waterLevel', 'waterFlow').",
    )


@mcp.tool(description="Get latest hydrology readings with station metadata.")
async def get_hydrology_readings(args: HydrologyReadingsInput) -> dict[str, Any]:
    """
    Fetches latest hydrology readings with basic parsing of station IDs.

    Returns:
      {
        "readings": [
          {
            "station_id": "...",
            "value": 1.23,
            "timestamp": "2025-11-21T12:00:00",
            "source": "hydrology",
            "measure_url": "..."
          }
        ],
        "count": 100
      }
    """
    readings_url = "https://environment.data.gov.uk/hydrology/data/readings.json"
    readings_params = {
        "latest": "",
        "observedProperty": args.observed_property,
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


class PublicRegisterSearchInput(BaseModel):
    postcode: str = Field(..., description="Postcode to search around, e.g. 'CT13 9ND'.")
    easting: int = Field(..., description="OS National Grid easting for the search point.")
    northing: int = Field(..., description="OS National Grid northing for the search point.")
    dist_km: int = Field(
        1,
        ge=1,
        le=10,
        description="Search radius in kilometres (1–10).",
    )


@mcp.tool(description="Search Environment Agency Public Registers near a location.")
async def search_public_registers(args: PublicRegisterSearchInput) -> dict[str, Any]:
    """
    Calls the CSV-based Public Register API and returns a JSON-ified view.

    Returns:
      {
        "entries": [ { ...columns... }, ... ],
        "meta": { "url": "...", "query": {...} }
      }
    """
    base_url = "https://environment.data.gov.uk/public-register/api/search.csv"
    params = {
        "__postcode": args.postcode,
        "dist": args.dist_km,
        "easting": args.easting,
        "northing": args.northing,
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


def main() -> None:
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()
