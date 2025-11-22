---
layout: default
title: Agentic Environmental Intelligence
---

# Agentic Environmental Intelligence

> **⚠️ Disclaimer**: This is a proof of concept and personal project for learning and demonstration purposes. It is **not** in production use and is not affiliated with or endorsed by the UK Environment Agency or any government organisation. Data accuracy and reliability are not guaranteed.

An AI-powered environmental monitoring system that autonomously detects, analyzes, and reports potential environmental incidents across England using real-time data from the UK Environment Agency.

## Overview

This system combines agentic AI workflows with environmental data APIs to provide intelligent, context-aware incident detection and analysis. It monitors flood levels, hydrology readings, and rainfall data, automatically identifying anomalies and correlating them with regulatory permits to provide actionable intelligence for environmental responders.

### Why Agents Beat Traditional Pipelines

Traditional ETL pipelines require predefined logic for every scenario. This agent **adapts based on what it finds**:

- **Flood event detected?** → Check rainfall correlation
- **No rainfall but high water?** → Search for discharge permits
- **Contamination spike?** → Look for upstream waste operations

The LLM makes intelligent decisions about which data to fetch and how to interpret it, creating a system that reasons rather than just executes.

## Real-World Example

**Date**: November 21, 2025  
**Location**: Somerset Levels  

**What the sensors showed:**
- Station 52157: 3.974m water level
- Station 52158: 3.744m water level
- Both exceeded 3.0m threshold

**What the agent figured out:**

1. **Detected & Clustered**: Grouped 2 nearby stations (~5km apart) as single incident
2. **Checked Rainfall**: 0mm in last 24 hours → ruled out recent meteorological cause
3. **Searched Permits**: Found 10 permits within 1km including 3 Wessex Water discharge permits
4. **Generated Insight**: 
   > "Elevated levels with no recent rainfall. Could be earlier rainfall (48-72h catchment lag) or Wessex Water discharge activity. Requires extended analysis window."

**Result**: Instead of a generic "high water" alert, responders got actionable intelligence about potential causes and specific follow-up actions.

**Key Learning**: The agent identified a limitation (24h rainfall window may miss earlier events) and recommended extending the analysis to 48-72h - demonstrating self-aware reasoning.

## Key Features

### 🤖 Autonomous Agent Workflow
- **LLM-driven decision making** using LangGraph and OpenAI GPT-4
- **Tool-based architecture** with specialized clients for different data sources
- **Adaptive data collection** - agent chooses what data to fetch based on findings
- **Self-aware reasoning** - identifies its own limitations and recommends improvements

### 📊 Multi-Source Data Integration
- **Flood Monitoring**: 761 stations monitoring river levels across England
- **Hydrology Data**: 1,000 stations tracking groundwater and flow rates
- **Rainfall Correlation**: 383 stations providing meteorological context (24h window, extensible to 48-72h)
- **Environmental Permits**: Public registers for discharge consents, waste operations, and flood risk activities

### 🎯 Intelligent Incident Detection
- **Threshold-based anomaly detection** identifying readings above safe levels
- **Spatial clustering** (10km radius) to identify localized incidents
- **Temporal filtering** (24-hour window) focusing on recent events
- **Multi-incident generation** creating separate reports for each geographic cluster

### 🌧️ Weather Context Integration
- **Rainfall correlation** for each flood cluster
- **Context-aware analysis**:
  - Heavy rainfall (>15mm): "Coincides with heavy rainfall"
  - Moderate (5-15mm): "Moderate rainfall detected"
  - None: "No significant rainfall - investigate non-meteorological causes"

### 📝 Data-Driven Alerts
- **Source-aware summaries** distinguishing flood vs hydrology incidents
- **Priority classification** (Low/Medium/High) based on severity
- **Permit analysis** identifying nearby regulated activities
- **Actionable recommendations** tailored to incident type

## Architecture

### Agent Graph
```
START → Initialize → Agent Decision → Tools → Process Results → Detect Anomalies → Generate Incidents → END
                         ↑                                           |
                         └───────────── Continue if needed ──────────┘
```

### Data Flow
1. **Collection**: Agent calls flood, hydrology, and rainfall APIs
2. **Processing**: Readings converted to standardized format with coordinate enrichment
3. **Detection**: Threshold-based anomaly detection (configurable)
4. **Clustering**: Spatial/temporal grouping of anomalies
5. **Enrichment**: Permit search and rainfall correlation per cluster
6. **Generation**: Context-aware incident reports with priority and actions

### Technology Stack
- **AI Framework**: LangChain + LangGraph for agentic workflows
- **LLM**: OpenAI GPT-4 for decision making and analysis
- **Storage**: MongoDB for incidents, PostgreSQL with pgvector for semantic search
- **APIs**: Environment Agency Flood Monitoring, Hydrology, Public Registers
- **Visualization**: Streamlit dashboard with Folium maps

## Example Incident Report

Here's an actual incident detected on November 21, 2025:

```
Incident ID: fe8f4d26-93fd-4f0a-a50c-bbfce0986b97
Priority: LOW (Monitoring Recommended)
Location: Somerset Levels (Othery area)
Coordinates: 51.079805°N, 2.869413°W

Affected Stations: 2
- Station 52157: 3.974m at 23:00 GMT
- Station 52158: 3.744m at 23:00 GMT

Summary:
Elevated river levels at 2 stations (52157, 52158). 
Peak: 3.97m, Average: 3.86m. 
Flood risk threshold: 3.0m. 
No significant rainfall in last 24h - investigate non-meteorological causes.
10 permits within 1km.

Analysis:
Peak reading 3.97m exceeds threshold by 32%. No rainfall detected 
in last 24 hours. River levels can lag behind rainfall events by 
48-72 hours depending on catchment characteristics.

Regulatory Context:
10 permits identified within 1km radius:
- 3x Wessex Water discharge permits (sewage pumping stations)
- 4x waste exemption registrations  
- 2x water quality exemptions
- 1x waste carrier registration

Possible explanations:
1. Earlier rainfall (48-72h ago) still affecting river levels
2. Upstream water management/discharge activity
3. Combination of both factors

Suggested Actions:
- Monitor river levels at stations 52157, 52158
- Check rainfall data for 48-72h window (extended catchment lag)
- Investigate if nearby permits contributed to elevated levels
- Contact Wessex Water regarding recent discharge activity
- Review historical patterns for this catchment area
```

### What This Demonstrates

**Data Correlation**: Connected flood monitoring + rainfall + permits across 3 separate APIs

**Intelligent Reasoning**: Identified the absence of rainfall as significant, suggesting non-meteorological causes

**Limitation Awareness**: Recognized that 24h rainfall window might miss earlier events, recommended 48-72h analysis

**Actionable Output**: Specific stations to monitor, permits to investigate, organizations to contact

## Incident Analysis

### Spatial Clustering
The system groups nearby anomalies (within 10km) to identify localized incidents rather than treating each reading as separate. This produces more actionable intelligence:

- **Before clustering**: 103 individual anomalous readings
- **After clustering**: 5 localized incidents requiring investigation

### Context-Aware Summaries
Alerts are tailored based on data source:

**Flood Incidents**:
- River levels and flood risk terminology
- Rainfall correlation analysis
- Focus on flood risk activities and discharge permits

**Hydrology Incidents**:
- Groundwater and flow rate language
- Emphasis on contamination risk
- Focus on waste operations and abstraction permits

## Performance

- **Data Collection**: ~15 seconds (9,000+ readings)
- **Anomaly Detection**: <1 second
- **Incident Generation**: ~5 seconds (including permit searches)
- **Total Runtime**: ~25-30 seconds end-to-end

## Data Coverage

| Data Source | Stations | Coverage | Coordinates |
|------------|----------|----------|-------------|
| Flood Monitoring | 761 | England-wide | 100% |
| Hydrology | 1,000 | England-wide | 100% |
| Rainfall | 383 | England-wide | 100% |
| Public Registers | Unlimited | Location-based | Via postcode/coordinates |

## Installation & Usage

See the [README](https://github.com/steve-dickinson/agentic-environmental-intelligence) for full installation instructions.

### Quick Start
```bash
# Clone repository
git clone https://github.com/steve-dickinson/agentic-environmental-intelligence.git
cd agentic-environmental-intelligence

# Start infrastructure
cd infra && docker-compose up -d

# Sync station metadata
uv run python scripts/sync_stations.py

# Run agent
uv run python scripts/run_agent.py

# Launch dashboard
uv run streamlit run streamlit_app.py
```

## Dashboard

The Streamlit dashboard provides:
- **Interactive map** with incident locations
- **Priority-based sorting** (High → Medium → Low)
- **Detailed incident cards** with readings, permits, and actions
- **Real-time data** refreshed from MongoDB

![Dashboard Screenshot](images/dashboard.png)

## Future Enhancements

The current system demonstrates the core capabilities, but there's significant potential for expansion:

### 🤝 Multi-Agent Collaboration
Split the monolithic agent into specialist roles working together:

- **FloodAnalystAgent**: Deep expertise in water levels, river flows, coastal monitoring
- **HydrologyAgent**: Groundwater, water quality, aquifer levels specialist
- **ComplianceAgent**: Permit regulations, facility compliance, violation detection
- **CommunicationsAgent**: Public-facing alerts, stakeholder notifications
- **CoordinatorAgent**: Orchestrates the specialists, synthesizes findings

**Why it matters**: Specialist agents with focused prompts and curated toolsets provide deeper analysis than a single generalist. The coordination overhead is worth it for better insights.

### 🔮 Predictive Intelligence
Shift from reactive (detecting floods) to proactive (forecasting floods):

**New Integration**: Met Office DataPoint API for weather forecasts

**Capabilities**:
- Predict flood risk 12-24 hours in advance
- Pattern recognition: "Last 3 floods preceded by >20mm rainfall in 12h"
- Confidence scoring: High (85%+), Medium (60-85%), Low (<60%)
- Time-to-threshold estimation: "Flood predicted in 10-12 hours"

**Example Output**:
```
HIGH CONFIDENCE FLOOD WARNING
River Severn at Gloucester predicted to exceed 3.5m in 10-12 hours.
Forecast: 35mm rainfall (vs historical pattern: 30mm+ → flooding).
Recommend pre-emptive notifications to riverside residents.
```

### 🌐 Cross-Domain Impact Analysis
Translate environmental data into human consequences:

**New Integrations**:
- **Ordnance Survey Places API**: Buildings, population density, critical infrastructure
- **Transport APIs**: National Rail, Highways England for disruption assessment
- **Property Data**: Land Registry for economic exposure estimation

**Enhanced Output**:
```
FLOOD PREDICTION: Reading Town Center
Environmental: 4.8m level expected in 10 hours

Human Impact:
- 3,247 residents in flood zone
- 2 care homes (77 elderly residents) - evacuate by T-6h
- 1 primary school (240 pupils) - early closure T-4h
- A329 closure required - 15,000 daily vehicles affected

Economic Impact:
- 842 residential properties (avg £385k)
- Estimated exposure: £324M
- 34 commercial properties
- Business disruption: £4.2M

Priority Actions:
1. Evacuate care homes by 14:00
2. Close A329 by 16:00, deploy diversions
3. Activate council emergency response plan
```

**Why it matters**: Stakeholders need to know *who's affected*, not just water levels. Economic impact numbers drive decision-making.

### 📢 Automated Alerting & Reporting
- **Daily briefings**: Executive summaries for Environment Agency
- **Stakeholder notifications**: Email/SMS to affected councils
- **Public updates**: Twitter/API for real-time information
- **Smart routing**: Agent decides who needs to know what, when, and through which channel

### 🔬 Enhanced Analysis Windows
- **Extended rainfall correlation**: 48-72 hour windows to account for catchment lag times
- **Historical pattern matching**: Compare current events to past incidents
- **Seasonal adjustments**: Different thresholds for winter vs summer
- **Soil saturation modeling**: Combine rainfall with ground conditions

### 📱 Mobile & Field Access
- Responsive dashboard for field teams
- Offline capability for remote areas
- Photo uploads and field notes
- Real-time status updates from responders

## Technical Highlights

### Coordinate Enrichment
All readings are enriched with full geospatial data:
- British National Grid (easting/northing)
- WGS84 coordinates (lat/lon)
- Enables spatial clustering and mapping

### Efficient Data Processing
- **Batch metadata loading**: Prevents N+1 database queries
- **Smart caching**: Reduces redundant API calls
- **Parallel tool execution**: Optimized for speed

### Extensible Architecture
- **MCP tools pattern**: Easy to add new data sources
- **Pluggable detectors**: Configurable anomaly detection
- **Modular clients**: Separated concerns for each API

## Contributing

Contributions welcome! Areas of interest:
- Additional data sources (air quality, water quality)
- Enhanced anomaly detection algorithms
- Improved permit categorization
- Dashboard enhancements

## License

MIT License - See LICENSE file for details

## Acknowledgments

Data provided by the UK Environment Agency under the Open Government Licence v3.0

---

Built with ❤️ using LangChain, LangGraph, and OpenAI
