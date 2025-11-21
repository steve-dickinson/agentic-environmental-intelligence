
import csv
import io

import httpx

from defra_agent.config import settings
from defra_agent.domain.models import Permit

PUBLIC_REGISTERS_SEARCH_URL = "https://environment.data.gov.uk/public-register/api/search.csv"


class PublicRegistersClient:
    async def fetch_permits_for_location(
        self,
        easting: int,
        northing: int,
        dist_km: int | None = None,
    ) -> list[Permit]:

        radius = dist_km or settings.public_registers_dist_km

        params = {
            "easting": easting,
            "northing": northing,
            "dist": radius,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(PUBLIC_REGISTERS_SEARCH_URL, params=params)
            resp.raise_for_status()
            csv_text = resp.text

        csv_file = io.StringIO(csv_text)
        reader = csv.DictReader(csv_file)
        rows = list(reader)

        permits: list[Permit] = []

        for row in rows:
            permit_id = row.get("registrationNumber") or row.get("@id") or ""
            operator = row.get("holder.name") or "Unknown operator"

            register_label = row.get("register.label")
            registration_type = row.get("registrationType.label") or row.get(
                "exemption.registrationType.notation",
            )

            site_address = row.get("site.siteAddress.address")
            site_postcode = row.get("site.siteAddress.postcode")

            distance_raw = row.get("distance")
            distance_km: float | None = None
            if distance_raw:
                try:
                    distance_km = float(distance_raw)
                except ValueError:
                    distance_km = None

            permits.append(
                Permit(
                    permit_id=str(permit_id),
                    operator_name=str(operator),
                    register_label=str(register_label) if register_label else None,
                    registration_type=str(registration_type) if registration_type else None,
                    site_address=str(site_address) if site_address else None,
                    site_postcode=str(site_postcode) if site_postcode else None,
                    distance_km=distance_km,
                ),
            )

        return permits
