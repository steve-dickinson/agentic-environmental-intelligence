#!/usr/bin/env python3
"""Check how many flood stations exist."""

import asyncio

import httpx


async def main() -> None:
    url = "https://environment.data.gov.uk/flood-monitoring/id/stations"

    total_fetched = 0
    page = 1

    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {"_limit": 500}

        while url:
            print(f"Fetching page {page}...")
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            print(f"  Got {len(items)} stations")
            total_fetched += len(items)

            # Find next link
            next_url = None
            for link in data.get("links", []):
                if link.get("rel") == "next":
                    next_url = link.get("href")
                    break

            if not next_url:
                break

            url = next_url
            params = {}  # Next URL already has params
            page += 1

    print(f"\nTotal flood monitoring stations: {total_fetched}")


if __name__ == "__main__":
    asyncio.run(main())
