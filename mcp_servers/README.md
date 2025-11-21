# Environment Agency MCP Server

Model Context Protocol (MCP) server exposing Environment Agency APIs as structured tools.

## Overview

This MCP server provides three tools for accessing UK environmental data:

1. **`get_flood_readings`** - Latest flood monitoring readings (water levels)
2. **`get_hydrology_readings`** - Latest hydrology readings (water flow, groundwater)
3. **`search_public_registers`** - Environmental permits near a location

## Tools

### get_flood_readings

Fetches latest flood monitoring readings from all stations across England.

**Parameters:**
- `parameter` (str, optional): Parameter to filter by. Default: `"level"`
  - Options: `"level"`, `"flow"`, etc.

**Returns:**
```json
{
  "readings": [
    {
      "station_id": "1029TH",
      "value": -0.079,
      "timestamp": "2025-11-21T19:00:00Z",
      "source": "flood",
      "measure_url": "https://..."
    }
  ],
  "count": 2012
}
```

### get_hydrology_readings

Fetches latest hydrology readings from all stations across England.

**Parameters:**
- `observed_property` (str, optional): Property to observe. Default: `"waterLevel"`
  - Options: `"waterLevel"`, `"waterFlow"`, `"groundwaterLevel"`, etc.

**Returns:**
```json
{
  "readings": [
    {
      "station_id": "48513a18",
      "value": 0.289,
      "timestamp": "2025-11-11T09:00:00",
      "source": "hydrology",
      "measure_url": "https://..."
    }
  ],
  "count": 7837
}
```

### search_public_registers

Searches Environment Agency Public Registers for environmental permits near a location.

**Parameters:**
- `postcode` (str, required): UK postcode to search around (e.g., "CT13 9ND")
- `easting` (int, required): OS National Grid easting coordinate
- `northing` (int, required): OS National Grid northing coordinate
- `dist_km` (int, optional): Search radius in kilometres (1-10). Default: `1`

**Returns:**
```json
{
  "entries": [
    {
      "holder.name": "COMPANY NAME",
      "registrationType.label": "Carrier Dealer",
      "register.label": "Waste Carriers and Brokers Public Register",
      "site.siteAddress.address": "...",
      "distance": "0.003..."
    }
  ],
  "meta": {
    "url": "https://...",
    "query": {...}
  }
}
```

## Running the Server

### Standalone Mode

Start the MCP server:

```bash
uv run python mcp_servers/ea_env_server.py
```

The server will run on stdio, ready to receive MCP protocol messages.

### Docker Mode

The server can be run in Docker using the provided Dockerfile:

```bash
cd infra
docker compose up mcp-ea-env
```

## Testing

Test all MCP tools without running the full MCP protocol:

```bash
uv run python scripts/test_mcp_server.py
```

This will:
- Fetch ~2000 flood readings
- Fetch ~8000 hydrology readings
- Search for permits near a test location (CT13 9ND)

## Integration with Agent

The MCP server can be used by the agent instead of direct API clients to demonstrate full MCP integration. This provides:

- **Standardized tool interface** - MCP protocol for all API interactions
- **Type-safe inputs** - Pydantic models validate all parameters
- **Structured outputs** - Consistent JSON responses
- **Composability** - Tools can be used by any MCP-compatible client

## API Sources

- **Flood Monitoring**: https://environment.data.gov.uk/flood-monitoring/doc/reference
- **Hydrology**: https://environment.data.gov.uk/hydrology/doc/reference
- **Public Registers**: https://environment.data.gov.uk/public-register

## Implementation Notes

### Station ID Extraction

Both flood and hydrology APIs return readings with `measure` fields containing URLs. The server extracts station IDs from these URLs:

```python
# Flood API: measure is a string URL
"measure": "https://environment.data.gov.uk/flood-monitoring/id/measures/1029TH-level-stage-i-15_min-mASD"
# Extract: "1029TH"

# Hydrology API: measure is a dict with @id
"measure": {"@id": "https://environment.data.gov.uk/hydrology/id/measures/48513a18-waterLevel-i-15_min-m"}
# Extract: "48513a18"
```

Station IDs are extracted by:
1. Getting the measure URL (from string or dict `@id`)
2. Taking the last path segment (measure ID)
3. Splitting on hyphen and taking the first part (station ID)

### Performance

The server returns raw readings without fetching individual station metadata to avoid timeout issues. Station metadata enrichment should be done by the client using a local station repository if needed.

## Future Enhancements

- [ ] Add tool for fetching specific station metadata
- [ ] Add caching for frequently accessed data
- [ ] Add filtering by geographic bounds
- [ ] Add batch processing for multiple locations
- [ ] Add historical data queries (not just latest)
