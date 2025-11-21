from defra_agent.domain.models import Reading


def detect_threshold_anomalies(
    readings: list[Reading],
    threshold: float,
) -> list[Reading]:
    """Return readings whose value exceeds the given threshold."""
    return [r for r in readings if r.value > threshold]
