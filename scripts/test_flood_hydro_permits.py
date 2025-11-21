#!/usr/bin/env python
"""
Demo: prove we can pull real data from

  - EA Flood Monitoring API (stations near a location)
  - EA Hydrology API (stations near the same location)
  - EA Public Registers API (permits near the same area, via postcode + easting/northing)

and do basic integrity checks.

This is deliberately simple and imperative so you can run it as:

    uv run python scripts/demo_flood_hydro_permits.py

Dependencies: `requests`
    uv add requests
"""

from __future__ import annotations

import csv
import io
from pprint import pprint
from typing import Any

import requests

# We'll use a real, concrete test location: CT13 9ND (Discovery Park, Sandwich).
# From public sources we know:
#   - lat: 51.286446
#   - long: 1.346237
#   - easting: 633430
#   - northing: 159464
# The easting/northing values match the pattern used in EA's own public-register
# example calls.
POSTCODE = "CT13 9ND"
LAT = 51.286446
LON = 1.346237
EASTING = 633430
NORTHING = 159464


def fetch_flood_stations(lat: float, lon: float, dist_km: float = 10.0) -> list[dict[str, Any]]:
    """
    Query EA Flood Monitoring API for stations near a given lat/long.

    Docs: https://environment.data.gov.uk/flood-monitoring/doc/reference
    Endpoint: /flood-monitoring/id/stations?lat=<>&long=<>&dist=<>
    """
    url = "https://environment.data.gov.uk/flood-monitoring/id/stations"
    params = {"lat": lat, "long": lon, "dist": dist_km}

    resp = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    stations: list[dict[str, Any]] = []

    for s in items:
        stations.append(
            {
                "stationReference": s.get("stationReference"),
                "label": s.get("label"),
                "lat": s.get("lat"),
                "long": s.get("long"),
                "easting": s.get("easting"),
                "northing": s.get("northing"),
            },
        )

    return stations


def fetch_hydrology_stations(
    lat: float,
    lon: float,
    dist_km: float = 10.0,
    observed_property: str = "waterLevel",
) -> list[dict[str, Any]]:
    """
    Query EA Hydrology API for stations near a given lat/long.

    Docs: https://environment.data.gov.uk/hydrology/doc/reference
    Example: /hydrology/id/stations?dist=10&lat=51.5074&long=-0.1278
    """
    url = "https://environment.data.gov.uk/hydrology/id/stations"
    params = {
        "lat": lat,
        "long": lon,
        "dist": dist_km,
        "observedProperty": observed_property,
    }

    resp = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    stations: list[dict[str, Any]] = []

    for s in items:
        stations.append(
            {
                "stationGuid": s.get("stationGuid"),
                "stationReference": s.get("stationReference"),
                "label": s.get("label"),
                "lat": s.get("lat"),
                "long": s.get("long"),
                "easting": s.get("easting"),
                "northing": s.get("northing"),
                "observedProperty": s.get("observedProperty"),
            },
        )

    return stations


def fetch_permits_near_postcode(
    postcode: str,
    easting: int,
    northing: int,
    dist_km: float = 1.0,
) -> tuple[list[dict[str, str]], str]:
    """
    Query EA Public Registers 'All Registers' API for entries near a given postcode/location.

    API: https://environment.data.gov.uk/public-register/api/search.csv
    Example pattern (from EA UI): ?__postcode=CT13+9ND&dist=1&easting=633428&northing=159463

    We request CSV and parse it into dicts.
    """
    url = "https://environment.data.gov.uk/public-register/api/search.csv"
    params = {
        "__postcode": postcode,
        "dist": dist_km,
        "easting": easting,
        "northing": northing,
    }

    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()

    csv_text = resp.text
    csv_file = io.StringIO(csv_text)
    reader = csv.DictReader(csv_file)
    rows: list[dict[str, str]] = list(reader)

    return rows, resp.url


def main() -> None:
    print("=== Environment Agency / Defra cross-API demo ===\n")

    print(f"Using area around postcode: {POSTCODE}")
    print(f"Lat/long:   {LAT}, {LON}")
    print(f"Easting/Northing: {EASTING}, {NORTHING}\n")

    # 1) Flood Monitoring stations
    print("1) Fetching Flood Monitoring stations near this location…")
    flood_stations = fetch_flood_stations(LAT, LON, dist_km=10.0)
    print(f"   → Found {len(flood_stations)} flood stations within 10 km")
    if flood_stations:
        print("   Example flood station:")
        pprint(flood_stations[0])

    # 2) Hydrology stations
    print("\n2) Fetching Hydrology stations near this location…")
    hydro_stations = fetch_hydrology_stations(
        LAT, LON, dist_km=10.0, observed_property="waterLevel"
    )
    print(f"   → Found {len(hydro_stations)} hydrology stations within 10 km")
    if hydro_stations:
        print("   Example hydrology station:")
        pprint(hydro_stations[0])

    # 3) Public Registers permits
    print("\n3) Fetching permits from Public Registers API near this postcode…")
    permits, api_url = fetch_permits_near_postcode(POSTCODE, EASTING, NORTHING, dist_km=1)
    print(f"   Public Registers API URL: {api_url}")
    print(f"   → Found {len(permits)} register entries within 1 km")
    if permits:
        print("   Example permit/registration row (raw):")
        example = permits[0]
        pprint(example)  # <--- see all keys & values
        print("\n   Available columns:")
        for key in example.keys():
            print(f"     - {key}")

    # 4) Basic sanity checks
    print("\n4) Sanity checks against expected structure:")
    flood_ok = bool(
        flood_stations
        and flood_stations[0].get("lat") is not None
        and flood_stations[0].get("long") is not None
    )
    hydro_ok = bool(
        hydro_stations
        and hydro_stations[0].get("lat") is not None
        and hydro_stations[0].get("long") is not None
    )

    example = permits[0] if permits else {}
    permits_ok = bool(
        permits
        and "holder.name" in example
        and "site.siteAddress.address" in example
        and ("register.label" in example or "registrationType.label" in example)
    )

    print(f"   Flood station has lat/long?           {flood_ok}")
    print(f"   Hydrology station has lat/long?       {hydro_ok}")
    print(f"   Permit row has Name+Address+Register? {permits_ok}")

    print("\nIf all the above are True and the sample records look sensible,")
    print("you’ve just proven that all three data sources are accessible and")
    print("can be aligned around a shared geography (same postcode/area).")


if __name__ == "__main__":
    main()
