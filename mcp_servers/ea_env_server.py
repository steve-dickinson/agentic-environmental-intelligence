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
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def _get_text(url: str, params: dict[str, Any] | None = None) -> str:
    logger.debug("GET %s params=%s", url, params)
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.text

class FloodReadingsInput(BaseModel):
    lat: float = Field(..., description="Latitude of the centre point.")
    long: float = Field(..., description="Longitude of the centre point.")
    dist_km: float = Field(
        10.0,
        description="Search radius in kilometres for stations.",
    )
    parameter: str = Field(
        "level",
        description="Parameter to filter readings by (e.g. 'level', 'flow').",
    )


@mcp.tool(
    "get_flood_readings",
    desc="Get latest flood-monitoring readings near a location.",
)
async def get_flood_readings(args: FloodReadingsInput) -> dict[str, Any]:
    """
    Returns:
      {
        "stations": [...],
        "readings": [...]
      }
    """

    stations_url = "https://environment.data.gov.uk/flood-monitoring/id/stations"
    stations_params = {
        "lat": args.lat,
        "long": args.long,
        "dist": args.dist_km,
    }
    stations_json = await _get_json(stations_url, stations_params)
    stations = stations_json.get("items", [])

    readings_url = "https://environment.data.gov.uk/flood-monitoring/data/readings"
    readings_params = {
        "latest": "",
        "parameter": args.parameter,
    }
    readings_json = await _get_json(readings_url, readings_params)
    readings = readings_json.get("items", [])

    return {
        "stations": stations,
        "readings": readings,
        "meta": {
            "stationsQuery": stations_params,
            "readingsQuery": readings_params,
        },
    }

class HydrologyStationsInput(BaseModel):
    lat: float = Field(..., description="Latitude of the centre point.")
    long: float = Field(..., description="Longitude of the centre point.")
    dist_km: float = Field(
        10.0,
        description="Search radius in kilometres for stations.",
    )
    observed_property: str = Field(
        "waterLevel",
        description="Hydrology observedProperty (e.g. 'waterLevel', 'waterFlow').",
    )


@mcp.tool(
    "get_hydrology_stations",
    desc="Get hydrology stations near a location.",
)
async def get_hydrology_stations(args: HydrologyStationsInput) -> dict[str, Any]:
    """
    Returns:
      {
        "stations": [...]
      }
    """
    url = "https://environment.data.gov.uk/hydrology/id/stations"
    params = {
        "lat": args.lat,
        "long": args.long,
        "dist": args.dist_km,
        "observedProperty": args.observed_property,
    }
    data = await _get_json(url, params)
    return {
        "stations": data.get("items", []),
        "meta": {"query": params},
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


@mcp.tool(
    "search_public_registers",
    desc="Search Environment Agency Public Registers near a location.",
)
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
