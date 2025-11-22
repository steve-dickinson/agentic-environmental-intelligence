from datetime import UTC, timedelta
from math import atan2, cos, radians, sin, sqrt

from defra_agent.domain.models import Reading


def cluster_anomalies_spatially(
    anomalies: list[Reading],
    max_distance_km: float = 10.0,
    min_cluster_size: int = 2,
) -> list[list[Reading]]:
    """Cluster anomalies by spatial proximity using simple distance-based clustering.

    Args:
        anomalies: List of anomalous readings with lat/lon coordinates
        max_distance_km: Maximum distance in km for two readings to be in same cluster
        min_cluster_size: Minimum number of readings to form a cluster

    Returns:
        List of clusters, where each cluster is a list of Reading objects
    """
    # Filter out readings without coordinates
    valid_anomalies = [a for a in anomalies if a.lat is not None and a.lon is not None]

    if not valid_anomalies:
        return []

    clusters: list[list[Reading]] = []
    used = set()

    for i, reading in enumerate(valid_anomalies):
        if i in used:
            continue

        # Start a new cluster
        cluster = [reading]
        used.add(i)

        # Find nearby readings
        for j, other in enumerate(valid_anomalies):
            if j in used or j == i:
                continue

            distance = _haversine_distance(reading.lat, reading.lon, other.lat, other.lon)

            if distance <= max_distance_km:
                cluster.append(other)
                used.add(j)

        # Only keep clusters that meet minimum size
        if len(cluster) >= min_cluster_size:
            clusters.append(cluster)

    # Sort clusters by size (largest first)
    clusters.sort(key=len, reverse=True)

    return clusters


def filter_recent_readings(
    readings: list[Reading],
    time_window_hours: int = 24,
) -> list[Reading]:
    """Filter readings to only include those within the specified time window.

    Args:
        readings: List of readings
        time_window_hours: Number of hours to look back

    Returns:
        List of readings within the time window
    """
    from datetime import datetime as dt

    cutoff = dt.now(UTC) - timedelta(hours=time_window_hours)

    recent = []
    for reading in readings:
        # Handle both datetime objects and strings
        ts = reading.timestamp
        if isinstance(ts, str):
            ts = dt.fromisoformat(ts.replace("Z", "+00:00"))

        # Ensure timestamp is timezone-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        if ts >= cutoff:
            recent.append(reading)

    return recent


def get_cluster_center(cluster: list[Reading]) -> tuple[float, float]:
    """Calculate the geographic center (centroid) of a cluster.

    Args:
        cluster: List of readings in the cluster

    Returns:
        Tuple of (lat, lon) representing the cluster center
    """
    valid_readings = [r for r in cluster if r.lat is not None and r.lon is not None]

    if not valid_readings:
        return (0.0, 0.0)

    avg_lat = sum(r.lat for r in valid_readings) / len(valid_readings)
    avg_lon = sum(r.lon for r in valid_readings) / len(valid_readings)

    return (avg_lat, avg_lon)


def get_cluster_postcode(cluster: list[Reading]) -> str:
    """Get a representative postcode for the cluster (using first station).

    This is a placeholder - in a real system you'd reverse geocode the centroid.

    Args:
        cluster: List of readings in the cluster

    Returns:
        A postcode string (placeholder implementation)
    """
    # For now, return empty - permits will be searched by lat/lon
    return ""


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in kilometers.

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates

    Returns:
        Distance in kilometers
    """
    # Earth's radius in kilometers
    R = 6371.0

    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c
