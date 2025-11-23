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
from defra_agent.storage.pgvector_repo import IncidentVectorRepository

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
        st.subheader("📚 Similar historical incidents (RAG)")

        # Use RAG to find similar past incidents
        if alerts:
            try:
                vector_repo = IncidentVectorRepository()
                query_text = alerts[0].get("summary", "")

                if query_text:
                    similar = vector_repo.find_similar_incidents(
                        query_text=query_text,
                        limit=3,
                        similarity_threshold=0.6,
                    )

                    # Filter out the current incident
                    current_id = incident.get("_id")
                    similar_filtered = [s for s in similar if s.incident_id != str(current_id)]

                    if similar_filtered:
                        st.markdown(
                            "**Found similar past incidents using vector similarity search:**"
                        )
                        for i, sim in enumerate(similar_filtered[:3], 1):
                            with st.expander(
                                f"{i}. Similarity: {sim.similarity:.1%} - {sim.summary[:80]}...",
                                expanded=(i == 1),
                            ):
                                st.markdown(f"**Incident ID:** `{sim.incident_id}`")
                                st.markdown(f"**Similarity Score:** {sim.similarity:.2%}")
                                st.markdown(f"**Summary:** {sim.summary}")
                                st.caption(
                                    "This incident was identified using semantic search (RAG) "
                                    "based on embedding similarity."
                                )
                    else:
                        st.info(
                            "No similar historical incidents found above 60% similarity threshold."
                        )
            except Exception as e:
                st.warning(f"RAG search unavailable: {e}")
        else:
            st.info("RAG search requires at least one alert to find similar incidents.")

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

    # ---------- RAG Query Testing ----------

    st.markdown("---")
    st.subheader("🔍 Test RAG Semantic Search")
    st.caption(
        "Try searching for incidents using natural language. "
        "RAG uses vector embeddings to find semantically similar incidents, not just keyword matches."
    )

    with st.expander("ℹ️ How RAG works", expanded=False):
        st.markdown("""
        **RAG (Retrieval-Augmented Generation)** uses vector embeddings to find similar incidents:
        
        1. Your query is converted to a 1536-dimensional vector using OpenAI embeddings
        2. We search the pgvector database for similar incident summaries using cosine similarity
        3. Results are ranked by similarity score (0-1, where 1.0 is identical)
        
        **Try these example queries:**
        - "Elevated river levels with no rainfall"
        - "High water detected in Somerset area"
        - "Groundwater contamination near industrial sites"
        - "Flood risk with upstream discharge"
        
        **What makes RAG powerful:**
        - Understands meaning, not just keywords
        - "high water" matches "elevated levels" (semantically similar)
        - Quantifies relevance with similarity scores
        - Fast: ~0.2 seconds to search thousands of incidents
        """)

    # Pre-defined example queries
    example_queries = [
        "Elevated river levels with no recent rainfall",
        "High water detected near Somerset Levels",
        "Groundwater contamination risk",
        "Flood risk with discharge permits nearby",
        "Multiple stations showing anomalous readings",
    ]

    col1, col2 = st.columns([3, 1])

    with col1:
        query_input = st.text_input(
            "Enter your query:",
            value="Elevated river levels with no recent rainfall",
            help="Describe what kind of incident you're looking for",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacer
        search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)

    # Example query buttons
    st.markdown("**Quick examples:**")
    cols = st.columns(5)
    for idx, example in enumerate(example_queries):
        if cols[idx % 5].button(
            example[:30] + "...", key=f"example_{idx}", use_container_width=True
        ):
            query_input = example
            search_clicked = True

    if search_clicked or query_input:
        try:
            vector_repo = IncidentVectorRepository()

            # Allow threshold adjustment
            threshold = st.slider(
                "Similarity threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.05,
                help="Minimum similarity score to include (0.0 = any match, 1.0 = exact match)",
            )

            with st.spinner("Searching vector database..."):
                results = vector_repo.find_similar_incidents(
                    query_text=query_input,
                    limit=10,
                    similarity_threshold=threshold,
                )

            if results:
                st.success(f"Found {len(results)} similar incidents (threshold: {threshold:.0%})")

                # Show results in a nice format
                for i, result in enumerate(results, 1):
                    # Determine color based on similarity
                    if result.similarity >= 0.9:
                        badge_color = "🟢"
                        badge_text = "Very high"
                    elif result.similarity >= 0.75:
                        badge_color = "🟡"
                        badge_text = "High"
                    elif result.similarity >= 0.6:
                        badge_color = "🟠"
                        badge_text = "Medium"
                    else:
                        badge_color = "⚪"
                        badge_text = "Low"

                    with st.expander(
                        f"{i}. {badge_color} {result.similarity:.1%} similarity ({badge_text}) - {result.summary[:100]}...",
                        expanded=(i <= 3),  # Expand top 3 results
                    ):
                        st.markdown(f"**Incident ID:** `{result.incident_id}`")
                        st.progress(result.similarity, text=f"Similarity: {result.similarity:.2%}")
                        st.markdown(f"**Full Summary:**\n\n{result.summary}")

                        # Try to get full incident details from MongoDB
                        try:
                            coll = get_incidents_collection()
                            full_incident = coll.find_one({"_id": result.incident_id})

                            if full_incident:
                                incident_summary = compute_incident_summary(full_incident)

                                st.markdown("---")
                                st.markdown("**Incident Details:**")

                                col_a, col_b, col_c = st.columns(3)
                                col_a.metric("Readings", incident_summary["reading_count"])
                                col_b.metric("Alerts", incident_summary["alert_count"])
                                col_c.metric("Permits", incident_summary["permit_count"])

                                if incident_summary["time"]:
                                    st.caption(
                                        f"Detected: {incident_summary['time'].strftime('%Y-%m-%d %H:%M')}"
                                    )
                        except Exception as e:
                            st.caption(f"Could not load full incident details: {e}")

                # Summary statistics
                st.markdown("---")
                st.markdown("**Search Statistics:**")
                avg_sim = sum(r.similarity for r in results) / len(results)
                max_sim = max(r.similarity for r in results)
                min_sim = min(r.similarity for r in results)

                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                stat_col1.metric("Results", len(results))
                stat_col2.metric("Avg Similarity", f"{avg_sim:.1%}")
                stat_col3.metric("Best Match", f"{max_sim:.1%}")
                stat_col4.metric("Worst Match", f"{min_sim:.1%}")

            else:
                st.info(
                    f"No incidents found above {threshold:.0%} similarity threshold. "
                    "Try lowering the threshold or using a different query."
                )
                st.markdown("**Suggestions:**")
                st.markdown("- Lower the similarity threshold slider")
                st.markdown(
                    "- Use more general terms (e.g., 'elevated levels' instead of specific values)"
                )
                st.markdown("- Try different phrasing")

        except Exception as e:
            st.error(f"RAG search error: {e}")
            st.caption("Make sure pgvector is running and incidents have been indexed.")

    st.markdown("---")
    st.info("""
    **📊 Future Enhancement: Knowledge Graph Comparison (Phase 2)**
    
    In Phase 2, we'll add a Knowledge Graph query interface alongside this RAG search.
    You'll be able to compare:
    
    - **RAG**: "Find similar incidents" (semantic similarity)
    - **Graph**: "What caused this incident?" (causal reasoning)
    
    Example:
    - RAG: "Elevated levels in Somerset" → finds similar events
    - Graph: "Which permits caused elevated levels via upstream discharge?" → traces causality
    
    Stay tuned!
    """)

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
