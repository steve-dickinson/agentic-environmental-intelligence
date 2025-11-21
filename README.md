# Agentic Environmental Intelligence

An agentic AI proof-of-concept that monitors environmental data from UK government APIs (DEFRA/Environment Agency), detects anomalies, and generates intelligent alerts using LangGraph and OpenAI.

## Quick Start

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
   
   Edit `.env` and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=your-api-key-here
   
   # Local database connections (for running without Docker)
   MONGO_URI=mongodb://localhost:27017
   PG_DSN=dbname=defra user=defra password=defra host=localhost
   ```

4. **Install dependencies**
   ```bash
   uv sync
   ```

5. **Install the package in editable mode**
   ```bash
   uv pip install -e .
   ```

6. **Start local databases** (MongoDB & PostgreSQL)
   ```bash
   cd infra
   sudo docker compose up -d mongo postgres
   cd ..
   ```
   
   **Note**: If you get permission errors, add your user to the docker group:
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

7. **Run the agent**
   ```bash
   uv run defra-agent-run
   ```

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
   sudo docker compose down
   ```

## What It Does

The agent:
1. **Fetches** latest environmental readings from UK government APIs
2. **Detects** anomalies in water levels, flows, and groundwater using statistical methods
3. **Generates** structured alerts with LLM-powered analysis (using OpenAI)
4. **Stores** incidents in MongoDB and embeddings in PostgreSQL (pgvector)
5. **Provides** actionable recommendations for each alert

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
- **Usage**: Search for environmental permits by location/station
- **Documentation**: [EA Public Registers](https://www.gov.uk/guidance/access-the-public-register-for-environmental-information)
- **Note**: Placeholder implementation for future enrichment

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_flood_client.py -v

# Run with coverage
uv run pytest --cov=src
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
│   ├── agent/          # LangGraph agent logic
│   ├── domain/         # Core models (Reading, Alert, Incident)
│   ├── services/       # Business logic (anomaly detection, summarization)
│   ├── storage/        # MongoDB and pgvector repositories
│   └── tools/          # API clients (flood, hydrology, permits)
├── scripts/            # Development and test scripts
├── tests/              # Unit tests
├── infra/              # Docker Compose and database init scripts
└── pyproject.toml      # Project configuration
```

## Configuration

Environment variables (`.env`):

```env
# Required
OPENAI_API_KEY=your-key-here

# Optional (with defaults)
OPENAI_MODEL=gpt-4.1-mini
ANOMALY_THRESHOLD=3.0

# Database connections
MONGO_URI=mongodb://localhost:27017
MONGO_DB=defra_agent
PG_DSN=dbname=defra user=defra password=defra host=localhost

# API endpoints (optional overrides)
PUBLIC_REGISTERS_BASE_URL=https://environment.data.gov.uk/public-register
```

## Data Flow

1. **FloodClient** → Fetches real-time readings from EA API
2. **AnomalyDetector** → Identifies outliers using z-score method (configurable threshold)
3. **AlertSummariser** → Uses OpenAI to generate structured alerts with priorities
4. **IncidentRepository** → Stores incidents in MongoDB
5. **IncidentVectorRepository** → Stores alert embeddings in PostgreSQL for similarity search

## Docker Services

- **mongo**: MongoDB 7 (port 27017)
- **postgres**: PostgreSQL 16 with pgvector extension (port 5432)
- **agent**: The Python agent application

## Example Usage

### Run a single detection cycle
```bash
uv run defra-agent-run
```

### Test individual components
```bash
# Test flood API client
uv run python scripts/test_flood_client.py

# Test anomaly detection
uv run python scripts/test_anomaly_flow.py

# Test incident service
uv run python scripts/test_incident_service.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This is a personal exploration project. See LICENSE for details.

## Acknowledgments

- Environment Agency for providing open environmental data APIs
- LangChain/LangGraph for the agentic framework
- OpenAI for LLM capabilities