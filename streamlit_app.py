#!/usr/bin/env python
from __future__ import annotations

import datetime as dt
from typing import Any

import httpx
import pandas as pd
import pydeck as pdk
import streamlit as st
from pymongo import MongoClient

from defra_agent.config import settings

# ---------- Mongo connection ----------


@st.cache_resource
def get_mongo_client() -> MongoClient:
    """Create and cache a MongoDB client."""
    return MongoClient(settings.mongo_uri)


def get_incidents_collection():
    client = get_mongo_client()
    return client[settings.mongo_db]["incidents"]


# ---------- Incident & readings helpers ----------


def load_all_incidents() -> list[dict[str, Any]]:
    """Fetch all incidents from Mongo, sorted by priority (high first) then by time."""
    coll = get_incidents_collection()
    docs = list(coll.find().sort("_id", -1))

    # Sort by priority: high > medium > low, then by time (newest first)
    priority_order = {"high": 3, "medium": 2, "low": 1}

    def sort_key(doc: dict[str, Any]) -> tuple[int, float]:
        summary = compute_incident_summary(doc)
        priority_score = priority_order.get(summary["highest_priority"], 0)
        time_score = summary["time"].timestamp() if summary["time"] else 0
        return (-priority_score, -time_score)  # Negative for descending order

    docs.sort(key=sort_key)
    return docs


def compute_incident_summary(doc: dict[str, Any]) -> dict[str, Any]:
    """Compute simple summary stats for an incident document."""
    readings = doc.get("readings", [])
    alerts = doc.get("alerts", [])
    permits = doc.get("permits", [])

    # derive "incident time" as latest reading timestamp
    incident_time: dt.datetime | None = None
    for r in readings:
        ts_str = r.get("timestamp")
        try:
            ts = pd.to_datetime(ts_str).to_pydatetime()
        except Exception:
            continue
        if incident_time is None or ts > incident_time:
            incident_time = ts

    priorities = [a.get("priority") for a in alerts if a.get("priority")]
    highest_priority = None
    if priorities:
        order = {"high": 3, "medium": 2, "low": 1}
        highest_priority = max(priorities, key=lambda p: order.get(p, 0))

    return {
        "time": incident_time,
        "reading_count": len(readings),
        "alert_count": len(alerts),
        "permit_count": len(permits),
        "highest_priority": highest_priority,
    }


def build_incident_options(docs: list[dict[str, Any]]) -> list[str]:
    """Build human-readable labels for the incident select box."""
    options: list[str] = []
    for idx, doc in enumerate(docs, 1):
        summary = compute_incident_summary(doc)
        readings = doc.get("readings", [])

        # Get station names and location
        station_ids = list({r.get("station_id") for r in readings if r.get("station_id")})[:2]
        station_text = ", ".join(station_ids) if station_ids else "Unknown location"

        # Get first reading's approximate location
        location_text = ""
        if readings and readings[0].get("lat") and readings[0].get("lon"):
            lat = readings[0]["lat"]
            lon = readings[0]["lon"]
            location_text = f"({lat:.2f}, {lon:.2f})"

        # Priority emoji
        priority_emoji = {
            "high": "🔴",
            "medium": "🟠",
            "low": "🟡",
        }.get(summary["highest_priority"], "ℹ️")

        # Build readable label
        label_parts = [
            f"#{idx}",
            priority_emoji,
            summary["highest_priority"] or "info",
            f"@ {station_text}",
        ]

        if location_text:
            label_parts.append(location_text)

        if summary["time"]:
            label_parts.append(summary["time"].strftime("%H:%M"))

        label = " ".join(label_parts)
        options.append(label)
    return options


def build_station_priority_map(
    alerts: list[dict[str, Any]],
    readings: list[dict[str, Any]],
) -> dict[str, str]:
    """
    Infer a priority per station_id by scanning alert text.

    For each reading.station_id, if that ID appears in an alert summary or actions,
    we assign the highest priority of all matching alerts.
    """
    order = {"high": 3, "medium": 2, "low": 1}
    station_ids = {r.get("station_id") for r in readings if r.get("station_id")}
    station_priority: dict[str, str] = {}

    for alert in alerts:
        priority = alert.get("priority")
        if priority not in order:
            continue
        score = order[priority]
        text = (alert.get("summary") or "") + " " + " ".join(alert.get("suggested_actions") or [])
        for sid in station_ids:
            if sid and sid in text:
                prev = station_priority.get(sid)
                prev_score = order.get(prev, 0)
                if score > prev_score:
                    station_priority[sid] = priority

    return station_priority


def build_readings_dataframe(
    readings: list[dict[str, Any]],
    station_priority: dict[str, str],
) -> pd.DataFrame:
    """
    Convert readings from Mongo into a DataFrame with lat/lon for mapping.

    Tailored to a schema like:

        {
          "station_id": "3400TH",
          "value": 4.537,
          "timestamp": "2025-11-21T15:00:00+00:00",
          "easting": 517700,
          "northing": 169800,
          "lat": 51.415005,
          "lon": -0.308869,
          "source": "flood"  # optional
        }
    """
    if not readings:
        return pd.DataFrame(
            columns=[
                "lat",
                "lon",
                "station_id",
                "source",
                "value",
                "timestamp",
                "priority",
            ]
        )

    rows: list[dict[str, Any]] = []

    for r in readings:
        lat = r.get("lat")
        lon = r.get("lon")
        station_id = r.get("station_id")
        source = r.get("source") or "unknown"
        value = r.get("value")
        ts_str = r.get("timestamp")

        # Skip anything without coordinates
        if lat is None or lon is None:
            continue

        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (TypeError, ValueError):
            continue

        try:
            timestamp = pd.to_datetime(ts_str)
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M") if pd.notna(timestamp) else "n/a"
        except Exception:
            timestamp = pd.NaT
            timestamp_str = "n/a"

        priority = station_priority.get(station_id, "none")

        rows.append(
            {
                "lat": lat_f,
                "lon": lon_f,
                "station_id": station_id,
                "source": source,
                "value": f"{value:.2f}" if value is not None else "n/a",
                "timestamp": timestamp,
                "timestamp_str": timestamp_str,
                "priority": priority.upper(),
            },
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "lat",
                "lon",
                "station_id",
                "source",
                "value",
                "timestamp",
                "priority",
            ]
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("timestamp", ascending=False)
    return df


# ---------- Geocoding for permits (by postcode) ----------


@st.cache_data(show_spinner=False)
def geocode_postcode(postcode: str) -> dict[str, float] | None:
    """
    Very simple geocoder using postcodes.io for PoC purposes.

    Returns {"lat": float, "lon": float} or None if not found.
    """
    if not postcode:
        return None

    normalized = postcode.strip().upper().replace(" ", "")
    url = f"https://api.postcodes.io/postcodes/{normalized}"
    try:
        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()
    except httpx.HTTPError:
        return None

    data = resp.json()
    result = data.get("result")
    if not result:
        return None

    lat = result.get("latitude")
    lon = result.get("longitude")
    if lat is None or lon is None:
        return None

    return {"lat": float(lat), "lon": float(lon)}


def build_permits_dataframe_with_coords(
    permits: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Convert permits from Mongo into a DataFrame with lat/lon using postcode geocoding.

    Each row also gets 'station_id', 'priority', 'value', 'timestamp' aliases
    so the shared tooltip template works for both sensors and permits.
    """
    if not permits:
        return pd.DataFrame(
            columns=[
                "lat",
                "lon",
                "operator_name",
                "site_postcode",
                "register_label",
                "registration_type",
                "distance_km",
                "station_id",
                "priority",
                "value",
                "timestamp",
            ]
        )

    rows: list[dict[str, Any]] = []

    for p in permits:
        postcode = p.get("site_postcode")
        geo = geocode_postcode(postcode) if postcode else None
        if not geo:
            continue  # skip permits we can't geocode

        operator = p.get("operator_name") or p.get("permit_id") or "Unknown permit"
        reg_type = p.get("registration_type") or ""
        reg_label = p.get("register_label") or ""
        dist = p.get("distance_km")

        # Build a readable "timestamp" surrogate for the tooltip
        if dist is not None:
            try:
                dist_str = f"{float(dist):.2f} km away"
            except (TypeError, ValueError):
                dist_str = str(dist)
        else:
            dist_str = "distance: n/a"

        timestamp_str = f"{postcode or 'No postcode'} | {dist_str}"
        value_str = reg_type or reg_label or "Permit"

        row = {
            "lat": geo["lat"],
            "lon": geo["lon"],
            "operator_name": operator,
            "site_postcode": postcode,
            "register_label": reg_label,
            "registration_type": reg_type,
            "distance_km": dist,
            # Aliases for the shared tooltip template
            "station_id": operator,  # shows as bold title
            "priority": "PERMIT",  # shows 'PERMIT' as the "priority"
            "value": value_str,  # shows type/label as 'value'
            "timestamp_str": timestamp_str,  # shows postcode + distance
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame(
            columns=[
                "lat",
                "lon",
                "operator_name",
                "site_postcode",
                "register_label",
                "registration_type",
                "distance_km",
                "station_id",
                "priority",
                "value",
                "timestamp",
            ]
        )

    df = pd.DataFrame(rows)
    # Nearest permits first
    if "distance_km" in df.columns:
        df = df.sort_values("distance_km", ascending=True)
    return df


# ---------- Streamlit UI ----------


def main() -> None:
    st.set_page_config(
        page_title="Defra Agentic Environmental Intelligence – POC",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🌊 Defra Agentic Environmental Intelligence (POC)")
    st.caption(
        "Internal agent that fuses EA Flood & Hydrology sensors with Environment Agency "
        "Public Registers to identify and prioritise potential environmental risk incidents."
    )

    # Sidebar: incident selection
    with st.sidebar:
        st.header("Incident explorer")

        incidents = load_all_incidents()
        if not incidents:
            st.info(
                "No incidents found in Mongo yet.\n\n"
                "Run the agent at least once to populate the database."
            )
            return

        options = build_incident_options(incidents)
        selected_label = st.selectbox("Select an incident", options)
        selected_index = options.index(selected_label)
        incident = incidents[selected_index]

        st.markdown("---")
        if st.button("🔄 Refresh incidents"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.experimental_rerun()

    # Summary for selected incident
    summary = compute_incident_summary(incident)
    readings = incident.get("readings", [])
    alerts = incident.get("alerts", [])
    permits = incident.get("permits", [])

    # Top-level tiles: tell the story quickly
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total readings analysed", summary["reading_count"])
    k2.metric("Alerts raised", summary["alert_count"])
    k3.metric("Permits in area", summary["permit_count"])
    k4.metric("Highest priority", summary["highest_priority"] or "n/a")

    # Build station-level priority map and DataFrame for map
    station_priority = build_station_priority_map(alerts, readings)
    df_readings = build_readings_dataframe(readings, station_priority)

    # Build DataFrame for permit locations (geocoded by postcode)
    df_permits_geo = build_permits_dataframe_with_coords(permits)

    # Main layout: map + narrative + permits
    left, right = st.columns([2, 1])

    # ---------- Map panel ----------

    with left:
        st.subheader("Where is the agent concerned? (sensors + permits)")

        # Debug: show what we're actually plotting
        with st.expander("Debug: sensor & permit dataframes", expanded=False):
            st.markdown("**Sensor readings (df_readings):**")
            st.write(df_readings.head(10))
            st.write("Columns:", list(df_readings.columns))
            st.markdown("**Permits (df_permits_geo):**")
            st.write(df_permits_geo.head(10))
            st.write("Columns:", list(df_permits_geo.columns))

        if df_readings.empty and df_permits_geo.empty:
            st.warning(
                "No readings with lat/lon and no geocoded permits for this incident. "
                "Check that lat/lon are stored on readings and that permits have valid postcodes."
            )
        else:
            # Choose a sensible centre: prefer readings, fallback to permits
            if not df_readings.empty:
                center_lat = df_readings["lat"].mean()
                center_lon = df_readings["lon"].mean()
            else:
                center_lat = df_permits_geo["lat"].mean()
                center_lon = df_permits_geo["lon"].mean()

            # --- Sensor points coloured by alert priority ---
            def priority_color(priority: str) -> list[int]:
                if priority == "high":
                    return [220, 20, 60]  # red
                if priority == "medium":
                    return [255, 140, 0]  # orange
                if priority == "low":
                    return [255, 215, 0]  # yellow
                return [100, 149, 237]  # blue for none/unknown

            sensor_layer = None
            if not df_readings.empty:
                df_readings["color"] = df_readings["priority"].apply(priority_color)

                sensor_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_readings,
                    get_position="[lon, lat]",
                    get_radius=400,  # station markers
                    get_fill_color="color",
                    pickable=True,
                    opacity=0.8,
                )

            # --- Permit points (geocoded) ---
            permit_layer = None
            if not df_permits_geo.empty:
                # Bright purple markers for permits
                df_permits_geo["color"] = [[180, 80, 255, 200] for _ in range(len(df_permits_geo))]

                permit_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_permits_geo,
                    get_position="[lon, lat]",
                    get_radius=300,  # permit markers (smaller than stations)
                    get_fill_color="color",
                    get_line_color=[255, 255, 255],
                    get_line_width=2,
                    line_width_min_pixels=1,
                    pickable=True,
                    opacity=0.9,
                )

            tooltip = {
                "html": (
                    "<b>{station_id}</b><br/>"
                    "Priority: {priority}<br/>"
                    "Value: {value}<br/>"
                    "{timestamp_str}"
                )
            }

            view_state = pdk.ViewState(
                latitude=center_lat,
                longitude=center_lon,
                zoom=9,
                pitch=0,
            )

            # IMPORTANT: permits first, stations second → stations render on top
            layers: list[pdk.Layer] = []
            if permit_layer is not None:
                layers.append(permit_layer)
            if sensor_layer is not None:
                layers.append(sensor_layer)

            st.pydeck_chart(
                pdk.Deck(
                    layers=layers,
                    initial_view_state=view_state,
                    tooltip=tooltip,
                )
            )

    # ---------- Right-hand panel: alerts + permits story ----------

    with right:
        st.subheader("Agent’s verdict for this incident")

        # Headline alert + list of all alerts
        if alerts:
            order = {"high": 3, "medium": 2, "low": 1}
            ordered = sorted(
                alerts,
                key=lambda a: order.get(a.get("priority", ""), 0),
                reverse=True,
            )
            top = ordered[0]
            st.markdown(f"**Headline alert:** {top.get('summary', '')}")
            st.markdown(f"**Priority:** `{top.get('priority', 'unknown')}`")

            if top.get("suggested_actions"):
                st.markdown("**Key suggested actions:**")
                for action in top["suggested_actions"]:
                    st.markdown(f"- {action}")

            st.markdown("---")
            st.markdown("**All alerts for this incident:**")
            for a in ordered:
                st.markdown(f"- `[{a.get('priority', 'n/a')}]` {a.get('summary', '')}")
        else:
            st.info("No alerts recorded – no significant anomalies were found.")

        st.markdown("---")
        st.subheader("Regulatory context (Public Registers permits)")

        if permits:
            permits_df = pd.DataFrame(permits)

            # Simple classification
            def classify(row: pd.Series) -> str:
                label = (row.get("register_label") or "").lower()
                if "waste" in label:
                    return "Waste"
                if "water quality" in label:
                    return "Water quality"
                if "discharges to water" in label:
                    return "Water quality"
                return "Other"

            permits_df["category"] = permits_df.apply(classify, axis=1)

            within_1km = permits_df[
                (permits_df["distance_km"].notna()) & (permits_df["distance_km"] <= 1.0)
            ]

            st.write(
                f"- **Total permits linked:** {len(permits_df)}\n"
                f"- **Within 1 km of the anomalous area:** {len(within_1km)}\n"
                f"- **By category:** "
                f"Waste ({(permits_df['category'] == 'Waste').sum()}), "
                f"Water quality ({(permits_df['category'] == 'Water quality').sum()}), "
                f"Other ({(permits_df['category'] == 'Other').sum()})"
            )

            st.markdown("**Nearest permit holders (top 10):**")
            if "distance_km" in permits_df.columns:
                permits_df = permits_df.sort_values("distance_km", ascending=True)

            preferred_cols = [
                "operator_name",
                "registration_type",
                "register_label",
                "site_address",
                "site_postcode",
                "distance_km",
                "category",
            ]
            cols = [c for c in preferred_cols if c in permits_df.columns] + [
                c for c in permits_df.columns if c not in preferred_cols
            ]
            st.dataframe(
                permits_df[cols].head(10),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No nearby permits were linked to this incident.")

    # ---------- Detailed tables ----------

    st.markdown("---")
    st.subheader("Detailed data")

    tab1, tab2 = st.tabs(["All alerts (table)", "All readings (raw)"])

    with tab1:
        if alerts:
            alerts_df = pd.DataFrame(alerts)
            st.dataframe(alerts_df, use_container_width=True, hide_index=True)
        else:
            st.info("No alerts for this incident.")

    with tab2:
        if readings:
            st.dataframe(
                pd.DataFrame(readings),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No stored readings for this incident.")


if __name__ == "__main__":
    main()
