---
layout: default
title: Agentic Environmental Intelligence
---

# Agentic Environmental Intelligence

> **⚠️ Disclaimer**: This is a proof of concept and personal project for learning and demonstration purposes. It is **not** in production use and is not affiliated with or endorsed by the UK Environment Agency or any government organisation. Data accuracy and reliability are not guaranteed.

An AI-powered environmental monitoring system that autonomously detects, analyzes, and reports potential environmental incidents across England using real-time data from the UK Environment Agency.

## Overview

This system combines agentic AI workflows with environmental data APIs to provide intelligent, context-aware incident detection and analysis. It monitors flood levels, hydrology readings, and rainfall data, automatically identifying anomalies and correlating them with regulatory permits to provide actionable intelligence for environmental responders.

## Key Features

### 🤖 Autonomous Agent Workflow
- **LLM-driven decision making** using LangGraph and OpenAI
- **Tool-based architecture** with specialized clients for different data sources
- **Adaptive data collection** based on detected anomalies

### 📊 Multi-Source Data Integration
- **Flood Monitoring**: 761 stations monitoring river levels across England
- **Hydrology Data**: 1,000 stations tracking groundwater and flow rates
- **Rainfall Correlation**: 383 stations providing meteorological context
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

```
Priority: HIGH
Location: 51.4105, -2.6043

Summary:
Elevated river levels at 2 stations (3400TH, 3404TH). 
Peak: 4.55m, Average: 4.15m. 
Flood risk threshold: 3.0m. 
No significant rainfall in last 24h - investigate non-meteorological causes.
10 discharge consents within 1km.

Suggested Actions:
- Monitor river levels at 3400TH, 3404TH
- Assess flood risk: 4.55m exceeds safe levels
- Review 10 discharge consents for compliance
```

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

- **Automated scheduling**: Cron-based monitoring cycles
- **Alerting system**: Email/SMS notifications for high-priority incidents
- **Historical analysis**: Trend detection and pattern recognition
- **Machine learning**: Predictive modeling for flood risk
- **Enhanced weather integration**: More comprehensive meteorological data
- **Mobile app**: Field access for responders

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
