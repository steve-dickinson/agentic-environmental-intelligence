import asyncio
import time

import httpx


async def main() -> None:
    print("Fetching rainfall data from API...")
    start = time.time()

    url = "https://environment.data.gov.uk/flood-monitoring/data/readings"
    params = {"latest": "", "parameter": "rainfall", "_limit": 10}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        data = resp.json()

    elapsed = time.time() - start
    items = data.get("items", [])
    print(f"✓ Fetched {len(items)} readings in {elapsed:.2f}s")

    if items:
        print("\nFirst reading:")
        print(f"  Measure: {items[0].get('measure')}")
        print(f"  Value: {items[0].get('value')}")
        print(f"  Time: {items[0].get('dateTime')}")


if __name__ == "__main__":
    asyncio.run(main())
