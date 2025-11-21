import asyncio
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from defra_agent.config import settings  # noqa: E402
from defra_agent.domain.anomaly_detector import detect_threshold_anomalies  # noqa: E402
from defra_agent.services.summariser import AlertSummariser  # noqa: E402
from defra_agent.tools.flood_client import FloodClient  # noqa: E402


async def main() -> None:
    print("Using model:", settings.openai_model)
    client = FloodClient()
    readings = await client.get_latest_readings()

    anomalies = detect_threshold_anomalies(readings, threshold=settings.anomaly_threshold)
    print(f"Total readings: {len(readings)}, anomalies: {len(anomalies)}")

    if not anomalies:
        print("No anomalies; exiting.")
        return

    summariser = AlertSummariser()
    alerts = await summariser.summarise(anomalies[:5])
    print("Sample alerts:")
    for alert in alerts:
        print(alert)


if __name__ == "__main__":
    asyncio.run(main())
