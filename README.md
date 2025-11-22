# Agentic Environmental Intelligence

An agentic AI proof-of-concept that monitors environmental data from UK government APIs (DEFRA/Environment Agency), detects anomalies, generates intelligent alerts using LangGraph and OpenAI, and provides an interactive Streamlit dashboard for incident visualization.

## TL;DR - Get Running in 5 Minutes

```bash
# 1. Clone and install
git clone https://github.com/steve-dickinson/agentic-environmental-intelligence.git
cd agentic-environmental-intelligence
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv (if needed)
source $HOME/.cargo/env  # Add uv to PATH

# 2. Configure
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-proj-your-key-here

# 3. Install dependencies
uv sync

# 4. Start databases
cd infra && docker compose up -d mongo postgres && cd ..

# 5. Sync station metadata (required for coordinates)
uv run python scripts/sync_stations.py

# 6. Run the agent (creates incidents)
uv run defra-agent-run

# 7. View the dashboard
uv run streamlit run streamlit_app.py
# Open http://localhost:8501 in your browser
```

## Features

- 🤖 **Autonomous Agent**: LangGraph-powered agent that continuously monitors environmental sensors
- 📊 **Interactive Dashboard**: Streamlit UI with map-based visualization of incidents, sensors, and permits
- 🔌 **MCP Integration**: Dual approach with LangChain @tool decorators for agents + FastMCP server for external clients
- 🌊 **Real-time Data**: Integrates Flood Monitoring, Hydrology, and Public Registers APIs
- 🚨 **Spatial & Temporal Clustering**: Groups anomalies by location (10km radius) and time (24 hours) for localized incident detection
- 🧠 **Context-Aware Alerts**: Data-driven summaries that adapt to flood vs hydrology readings with relevant permit analysis
- 🗺️ **Geospatial Intelligence**: Maps sensors and nearby environmental permits with color-coded priorities
- 💾 **Persistent Storage**: MongoDB for incidents, PostgreSQL/pgvector for embeddings

## Key Highlights

This project demonstrates:
- **Agentic AI workflows** using LangGraph for autonomous environmental monitoring
- **Multi-source data fusion** combining sensor readings with regulatory permit data
- **Geospatial intelligence** visualizing environmental risks on interactive maps
- **Production-ready patterns** including Docker deployment, MCP integration, and structured logging
- **UK Government API integration** showing how to work with real-world environmental data

## Quick Start

### First Time Setup Checklist

Before you begin, make sure you have:

- [ ] Python 3.12 or higher installed (`python --version`)
- [ ] Docker and Docker Compose installed (`docker --version`)
- [ ] An OpenAI API key (get one at https://platform.openai.com/api-keys)
- [ ] At least 2GB of free disk space
- [ ] Ports 27017, 5432, and 8501 available

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker & Docker Compose (for containerized deployment)
- OpenAI API key

**Note for WSL/Linux users**: The uv installation script works on WSL. For Windows users, see [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for Windows-specific instructions.

### Local Setup with uv

1. **Clone the repository**
   ```bash
   git clone https://github.com/steve-dickinson/agentic-environmental-intelligence.git
   cd agentic-environmental-intelligence
   ```

2. **Install uv** (if not already installed)
   
   **Linux/WSL/macOS:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   
   **Windows:**
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Create `.env` file**
   ```bash
   cp .env.example .env
   ```
   
   **Edit `.env`** with your favorite text editor and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=sk-proj-your-actual-key-here
   ```
   
   The other settings have sensible defaults and can be left as-is for local development.
   
   **Important**: Never commit your `.env` file to version control! It's already in `.gitignore`.

4. **Install dependencies**
   ```bash
   uv sync
   ```
   
   This will create a virtual environment and install all required packages including the project itself.

5. **Start local databases** (MongoDB & PostgreSQL)
   ```bash
   cd infra
   docker compose up -d mongo postgres
   cd ..
   ```
   
   **Note**: If you get a permission error, you may need to use `sudo`:
   ```bash
   sudo docker compose up -d mongo postgres
   ```
   
   Or add your user to the docker group (requires logout/login):
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

6. **Verify databases are running**
   ```bash
   docker ps
   ```
   
   You should see `mongo:7` and `pgvector/pgvector:pg16` containers running.

7. **Run the agent** (this creates your first incident)
   ```bash
   uv run defra-agent-run
   ```
   
   The agent will:
   - Fetch environmental readings from EA APIs
   - Detect anomalies
   - Generate alerts
   - Store the incident in MongoDB
   
   **Expected output**: You should see log messages about fetching readings, detecting anomalies, and storing incidents.

8. **Launch the Streamlit dashboard** (in a separate terminal)
   ```bash
   uv run streamlit run streamlit_app.py
   ```
   
   The dashboard will open at http://localhost:8501 and display:
   - Interactive map of sensor locations and permit holders
   - Incident timeline and alert priorities
   - Regulatory context from Public Registers
   - Detailed readings and alert data

### Quick Validation

Verify your setup is working:

```bash
# 1. Check databases are running
docker ps | grep -E "mongo|postgres"

# 2. Test the anomaly detection workflow
uv run python scripts/test_anomaly_flow.py

# 3. Run the agent and check for errors
uv run defra-agent-run

# 4. Open the dashboard
uv run streamlit run streamlit_app.py
```

You should see:
- ✅ Two Docker containers running (mongo and postgres)
- ✅ Test script fetches readings and generates alerts
- ✅ Agent completes without errors and stores incident
- ✅ Dashboard shows at least one incident on the map

### Docker Setup

Run the entire application stack (agent + databases) using Docker Compose:

1. **Create `.env` file** (if not already done)
   ```bash
   cp .env.example .env
   ```
   Add your OpenAI API key to `.env`

2. **Build and start all services**
   ```bash
   cd infra
   sudo docker compose up --build
   ```
   
   **Note**: If you get permission errors, add your user to the docker group:
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. **View logs**
   ```bash
   sudo docker compose logs -f agent
   ```

4. **Stop services**
   ```bash
   cd infra
   docker compose down
   ```
   
   **Note**: The agent service in Docker Compose will run once and exit. This is expected behavior. The databases will continue running.

5. **Access the Streamlit dashboard**
   
   The dashboard runs separately (not in Docker). After the agent has populated the database:
   ```bash
   # From the project root directory
   uv run streamlit run streamlit_app.py
   ```
   
   Open http://localhost:8501 in your browser.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit Dashboard                        │
│              (Interactive incident visualization)               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                     LangGraph Agent                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Fetch Readings → 2. Detect Anomalies →             │   │
│  │  3. Generate Alerts → 4. Find Permits →                │   │
│  │  5. Store Incidents                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└───┬─────────────────┬──────────────────┬────────────────────────┘
    │                 │                  │
┌───▼──────┐  ┌───────▼──────┐  ┌────────▼────────┐
│ MongoDB  │  │ PostgreSQL   │  │   MCP Server    │
│(Incidents)│  │  (pgvector)  │  │  (EA API Tools) │
└──────────┘  └──────────────┘  └─────────────────┘
```

### MCP Integration

The project demonstrates **two approaches** to MCP (Model Context Protocol):

#### 1. LangChain Tools (Recommended for LangGraph agents)

Location: `src/defra_agent/tools/mcp_tools.py`

These are `@tool` decorated functions that can be called directly by LangGraph agents:

- **`get_flood_readings`**: Fetch latest flood monitoring readings
  - Parameter: `parameter` (e.g., 'level', 'flow')
  - Returns: List of readings with station IDs, values, timestamps
  
- **`get_hydrology_readings`**: Fetch latest hydrology readings
  - Parameter: `observed_property` (e.g., 'waterLevel', 'waterFlow')
  - Returns: List of readings with station IDs, values, timestamps
  
- **`search_public_registers`**: Search environmental permits by location
  - Parameters: `postcode`, `easting`, `northing`, `dist_km`
  - Returns: List of permit entries with operator details

**Usage**: These tools are integrated into the agent graph via `ToolNode` for intelligent, LLM-driven data retrieval.

**Test**: `uv run python scripts/test_mcp_tools.py`

#### 2. FastMCP Server (For external MCP clients)

Location: `mcp_servers/ea_env_server.py`

A standalone MCP server using FastMCP protocol that exposes the same tools via stdio/HTTP for external clients like Claude Desktop.

**Run**: `uv run python mcp_servers/ea_env_server.py`

**Test**: `uv run python scripts/test_mcp_server.py`

See `docs/MCP_INTEGRATION.md` for detailed architecture and usage patterns.

## What It Does

### Agent Workflow

1. **Fetches** latest environmental readings from EA Flood Monitoring and Hydrology APIs
2. **Detects** anomalies in water levels, flows, and groundwater using statistical z-score method
3. **Clusters** anomalies spatially (10km radius) and temporally (24 hours) to identify localized incidents
4. **Searches** for nearby environmental permits within 1km of each cluster center
5. **Generates** context-aware alerts with data-driven analysis including:
   - Priority levels (high/medium/low) based on threshold exceedance
   - Flood-aware summaries (river levels, flood risk) or hydrology-aware summaries (groundwater, contamination risk)
   - Specific station IDs, peak/average values, and threshold context
   - Permit type categorization (flood risk activities, discharge consents, waste operations)
   - Suggested actions tailored to the source type and nearby permit types
6. **Stores** complete incidents in MongoDB with cluster-specific readings, alerts, and permits

### Dashboard Features

The Streamlit dashboard (`streamlit_app.py`) provides:

- **Interactive Map**: Visualize sensor locations color-coded by alert priority (red=high, orange=medium, yellow=low)
- **Permit Overlay**: Geocoded environmental permit holders displayed as purple markers
- **Incident Selector**: Browse incidents sorted by priority with station IDs, coordinates, and timestamps
- **Alert Analysis**: View data-driven summaries with specific values, thresholds, and context
- **Regulatory Context**: See nearby permits categorized by type (flood risk, waste, discharge)
- **Data Tables**: Detailed readings with coordinates, alerts with priorities, and permit information
- **Map Tooltips**: Hover over markers to see station details, readings, and permit locations

## API Endpoints Used

### Environment Agency Flood Monitoring API
- **Base URL**: `https://environment.data.gov.uk/flood-monitoring`
- **Endpoint**: `/data/readings?latest&parameter=level`
- **Documentation**: [EA Real Time Flood Monitoring API](https://environment.data.gov.uk/flood-monitoring/doc/reference)
- **Usage**: Fetches latest water level readings from monitoring stations across England
- **Features**:
  - Real-time data
  - No authentication required
  - Returns JSON with station IDs, values, and timestamps
  - Supports retry logic for resilience

### Environment Agency Hydrology API
- **Base URL**: `https://environment.data.gov.uk/hydrology`
- **Endpoint**: `/data/readings?latest&parameter=flow`
- **Documentation**: [EA Hydrology Data](https://environment.data.gov.uk/hydrology/doc/reference)
- **Usage**: Fetches flow, groundwater, and other hydrological data
- **Note**: Currently experimental in this project

### Environment Agency Public Registers API
- **Base URL**: `https://environment.data.gov.uk/public-register`
- **Endpoint**: `/api/search.csv`
- **Documentation**: [EA Public Registers](https://www.gov.uk/guidance/access-the-public-register-for-environmental-information)
- **Usage**: Search for environmental permits (waste, water discharge, etc.) by location
- **Features**:
  - CSV-based API
  - Searches by postcode + radius (km)
  - Returns permit details, operator names, site addresses
  - Integrated into agent for regulatory context enrichment
  
### Postcodes.io (for geocoding)
- **URL**: `https://api.postcodes.io`
- **Usage**: Convert permit postcodes to lat/lon coordinates for map visualization
- **License**: Open Government License (OGL)

## Development

### Running Tests

```bash
# Install dev dependencies first (includes pytest)
uv sync --extra dev

# Run all tests (currently limited test coverage)
uv run pytest

# Run specific test file
uv run pytest tests/test_flood_client.py -v

# Run with coverage
uv run pytest --cov=src

# Run script-based tests (more comprehensive, no dev deps needed)
uv run python scripts/test_anomaly_flow.py
uv run python scripts/test_mcp_tools.py
```

### Code Quality

```bash
# Format code
uv run ruff format src

# Lint and auto-fix
uv run ruff check src --fix

# Type checking
uv run mypy src
```

### Project Structure

```
├── src/defra_agent/
│   ├── agent/          # LangGraph agent logic and workflow orchestration
│   │   ├── graph.py          # Clustering-based detection with context-aware alerts
│   │   └── main.py           # Agent entry point
│   ├── domain/         # Core models and business logic
│   │   ├── models.py           # Reading, Alert, Incident data models
│   │   ├── anomaly_detector.py # Z-score based anomaly detection
│   │   └── clustering.py       # Spatial/temporal clustering (10km/24h)
│   ├── services/       # Application services
│   │   ├── incident_service.py # End-to-end incident creation workflow
│   │   └── summariser.py       # Alert summarization (currently unused - using data-driven approach)
│   ├── storage/        # Persistence layer
│   │   ├── mongo_repo.py       # Incident repository (MongoDB)
│   │   ├── pgvector_repo.py    # Vector embeddings (PostgreSQL)
│   │   └── station_repo.py     # Station metadata with coordinates
│   ├── tools/          # API clients and MCP tools
│   │   ├── flood_client.py         # Flood API with coordinate enrichment
│   │   ├── hydrology_client.py     # Hydrology API with coordinate enrichment
│   │   ├── public_registers_client.py  # Permit search by coordinates
│   │   └── mcp_tools.py            # LangChain @tool decorators for agent
│   └── config.py       # Pydantic settings and environment configuration
├── mcp_servers/
│   ├── ea_env_server.py  # FastMCP server for external clients
│   └── README.md         # MCP server documentation
├── docs/
│   └── MCP_INTEGRATION.md  # MCP architecture and usage guide
├── scripts/            # Development and test scripts
│   ├── sync_stations.py        # Populate station metadata repository
│   ├── run_agent.py            # Execute agent workflow
│   └── test_*.py               # Various integration tests
├── tests/              # Unit tests
├── infra/              # Docker Compose and database initialization
├── streamlit_app.py    # Interactive dashboard for incident visualization
├── main.py             # Simple entry point placeholder
└── pyproject.toml      # Project configuration and dependencies
```

## Configuration

The project uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

```env
# ============ REQUIRED ============
OPENAI_API_KEY=sk-proj-your-key-here  # Get from: https://platform.openai.com/api-keys

# ============ OPTIONAL ============
# Model configuration
OPENAI_MODEL=gpt-4.1-mini              # Options: gpt-4, gpt-4-turbo, gpt-4.1-mini

# Anomaly detection sensitivity
ANOMALY_THRESHOLD=3.0                  # Z-score threshold (higher = fewer alerts)
                                       # 3.0 = ~99.7% confidence interval
                                       # 2.0 = ~95% confidence interval

# Public register search radius
PUBLIC_REGISTERS_DIST_KM=3             # Search radius in km for permits (1-10)

# ============ DATABASE CONNECTIONS ============
# Local development (databases in Docker, agent on host)
MONGO_URI=mongodb://localhost:27017
MONGO_DB=defra_agent
PG_DSN=dbname=defra user=defra password=defra host=localhost

# Docker deployment (agent also in Docker - uncomment if needed)
# MONGO_URI=mongodb://mongo:27017
# PG_DSN=dbname=defra user=defra password=defra host=postgres
```

**Configuration Tips:**
- Start with defaults and adjust `ANOMALY_THRESHOLD` if you want more/fewer alerts
- `gpt-4.1-mini` is faster and cheaper; upgrade to `gpt-4` for better analysis
- Database URIs change based on where the agent runs (host vs Docker)

## Data Flow

1. **FloodClient** → Fetches real-time readings from EA Flood Monitoring API with coordinate enrichment from StationMetadataRepository
2. **HydrologyClient** → Fetches flow and groundwater data from EA Hydrology API with coordinate enrichment
3. **AnomalyDetector** → Identifies outliers using z-score method (configurable threshold)
4. **Clustering Module** → Groups anomalies spatially (10km radius) and filters to recent 24 hours
5. **PublicRegistersClient** → Searches for environmental permits within 1km of each cluster center
6. **Context-Aware Alert Generator** → Creates data-driven summaries based on source type:
   - **Flood readings**: "Elevated river levels" with flood risk assessment and flow-related permit analysis
   - **Hydrology readings**: "Anomalous groundwater" with contamination risk and waste permit analysis
   - Specific station IDs, peak/average values, threshold exceedance percentages
   - Suggested actions tailored to reading type and nearby permit categories
7. **IncidentRepository** → Stores one incident per cluster with cluster-specific readings, alerts, and permits in MongoDB
8. **Streamlit Dashboard** → Visualizes incidents, sensors, and permits on an interactive map with priority-based sorting

## Example Usage

### Run the complete workflow

**Important**: Always run the agent BEFORE launching the dashboard to ensure data exists.

```bash
# 1. Start databases (if not using Docker for everything)
cd infra
docker compose up -d mongo postgres
cd ..

# 2. Run agent to detect anomalies and create incidents (REQUIRED FIRST)
uv run defra-agent-run

# 3. Launch dashboard to explore incidents (in a separate terminal)
uv run streamlit run streamlit_app.py
```

**Tip**: Run the agent periodically (e.g., via cron) to accumulate incidents over time.

### Test individual components
```bash
# Test anomaly detection workflow (generates alerts from flood data)
uv run python scripts/test_anomaly_flow.py

# Test flood and hydrology API integration with permits
uv run python scripts/test_flood_hydro_permits.py

# Test hydrology client
uv run python scripts/test_hydrology_client.py

# Test incident service end-to-end
uv run python scripts/test_incident_service.py

# Test MCP tools (LangChain @tool integration)
uv run python scripts/test_mcp_tools.py

# Test MCP server directly
uv run python scripts/test_mcp_server.py

# Sync monitoring stations to database
uv run python scripts/sync_stations.py
```

### Run MCP Server
```bash
# Start the MCP server for EA environment data
uv run python mcp_servers/ea_env_server.py
```

## Docker Services

The Docker Compose setup (`infra/docker-compose.yml`) includes:

- **mongo**: MongoDB 7 (port 27017) - stores incident documents
- **postgres**: PostgreSQL 16 with pgvector extension (port 5432) - stores embeddings
- **agent**: The Python agent application (optional containerized deployment)

## Screenshots

The Streamlit dashboard provides:
- **Map View**: Sensors color-coded by alert priority with permit overlay
- **Incident Metrics**: Reading count, alerts raised, permit count, highest priority
- **Alert Details**: AI-generated summaries and recommended actions
- **Regulatory Context**: Nearby permits categorized by type (waste, water quality, etc.)
- **Data Tables**: Full incident, reading, and permit data for analysis

## Troubleshooting

### "No incidents found" in Streamlit dashboard

**Cause**: The agent hasn't run yet or didn't create any incidents.

**Solution**: Run the agent at least once:
```bash
uv run defra-agent-run
```

### "OpenAI API key not set" error

**Cause**: Missing or invalid `OPENAI_API_KEY` in `.env` file.

**Solution**:
1. Get an API key from https://platform.openai.com/api-keys
2. Add it to your `.env` file:
   ```env
   OPENAI_API_KEY=sk-proj-...
   ```
3. Restart the agent

### Port conflicts (27017, 5432, 8501)

**Cause**: Another service is using the same port.

**Solution**: Either stop the conflicting service or modify ports in:
- `infra/docker-compose.yml` for database ports
- Streamlit uses `--server.port` flag: `uv run streamlit run streamlit_app.py --server.port 8502`

### Database connection errors

**Cause**: Databases not running or wrong connection string.

**Solution**:
1. Check containers are running: `docker ps`
2. Verify connection strings in `.env`:
   - Local dev: `MONGO_URI=mongodb://localhost:27017`
   - Docker agent: `MONGO_URI=mongodb://mongo:27017`

### "uv: command not found"

**Cause**: uv not installed or not in PATH.

**Solution**:
```bash
# Linux/WSL/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### No anomalies detected

**Cause**: Environmental readings are all normal (this is good!).

**Solution**: The agent is working correctly. Anomalies are rare. To test with synthetic anomalies:
```bash
uv run python scripts/test_anomaly_flow.py
```

### Streamlit map not showing data

**Cause**: Readings missing lat/lon coordinates or geocoding failed.

**Solution**: Check the debug expander in the dashboard to see the actual dataframes. Permit geocoding requires valid UK postcodes.

## FAQ

### How often should I run the agent?

The agent is designed to run on-demand or via scheduled tasks (cron/systemd). Each run:
- Fetches the **latest** readings from EA APIs
- Detects anomalies in that snapshot
- Creates one incident per run (if anomalies found)

For continuous monitoring, schedule it to run every 15-60 minutes.

### Does this work with live data?

Yes! The agent fetches real-time data from Environment Agency APIs. The data is as current as the EA's monitoring stations report it (typically updated every 15 minutes).

### Why am I not seeing any anomalies?

This is actually normal! Environmental readings are usually stable. The z-score threshold of 3.0 means you only get alerts when readings are >3 standard deviations from the mean - which is rare.

To test the system works:
- Lower the threshold to 2.0 in `.env`
- Run `uv run python scripts/test_anomaly_flow.py` for synthetic data

### Can I use this for other locations besides the UK?

The EA APIs only cover England. To adapt for other regions, you'd need to:
1. Find equivalent APIs for your region
2. Update the client code in `src/defra_agent/tools/`
3. Adjust the data models if schemas differ

### How much does this cost to run?

Costs depend on OpenAI API usage:
- **Per agent run**: ~$0.01-0.05 (varies with number of anomalies and gpt-4.1-mini pricing)
- **Storage**: Negligible (local MongoDB/PostgreSQL are free)
- **APIs**: Environment Agency APIs are free and open

Estimated monthly cost for hourly runs: $15-30

### Is there a web interface for the agent?

Yes! The Streamlit dashboard provides an interactive UI. However, it's read-only - you can't trigger agent runs from it. Use `uv run defra-agent-run` to create new incidents.

### Can I deploy this to production?

This is a proof-of-concept, but it includes production-ready patterns:
- ✅ Docker Compose for easy deployment
- ✅ Environment-based configuration
- ✅ Structured logging
- ✅ Database persistence
- ⚠️ Add authentication for Streamlit in production
- ⚠️ Set up proper monitoring and alerting
- ⚠️ Consider rate limits on EA APIs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This is a personal exploration project. Use at your own discretion.

## Acknowledgments

- **Environment Agency** for providing open environmental data APIs:
  - [Flood Monitoring API](https://environment.data.gov.uk/flood-monitoring/doc/reference)
  - [Hydrology API](https://environment.data.gov.uk/hydrology/doc/reference)
  - [Public Registers API](https://environment.data.gov.uk/public-register)
- **LangChain/LangGraph** for the agentic framework
- **OpenAI** for LLM capabilities
- **Streamlit** for rapid dashboard development
- **Postcodes.io** for UK postcode geocoding
- **Model Context Protocol (MCP)** for structured tool interfaces

## Technologies Used

- **Python 3.12+** with uv package manager
- **LangGraph** - Agent workflow orchestration
- **OpenAI GPT-4** - Natural language processing and analysis
- **Streamlit** - Interactive data visualization dashboard
- **PyDeck** - WebGL-powered geospatial visualizations
- **MongoDB** - Document storage for incidents
- **PostgreSQL + pgvector** - Vector embeddings storage
- **MCP (Model Context Protocol)** - Structured API tool interfaces
- **Docker Compose** - Multi-container orchestration
- **Pydantic** - Data validation and settings management