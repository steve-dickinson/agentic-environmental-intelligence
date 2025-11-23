---
layout: default
title: Project Evolution & Changelog
---

**Navigation**: [Home](index.md) | [Changelog](changelog.md) | [Architecture](architecture.md) | [GitHub](https://github.com/steve-dickinson/agentic-environmental-intelligence)

# Project Evolution & Changelog

This page tracks the iterative development of the Agentic Environmental Intelligence system, showing how it evolved from a basic proof-of-concept to a sophisticated RAG-powered monitoring system.

> **Philosophy**: Each iteration adds real value, not just complexity. We build, test, learn, and document before moving to the next phase.

---

## Version History

### RAG-Powered Semantic Search ✅
**Released**: November 23, 2025  
**Status**: Complete

#### What We Added
- **Vector embeddings** using OpenAI text-embedding-3-small (1536 dimensions)
- **pgvector integration** for fast similarity search with PostgreSQL
- **Automatic RAG enrichment** during incident generation
- **Interactive query interface** in Streamlit dashboard
- **Historical context** displayed for each incident

#### Technical Implementation
- `IncidentVectorRepository` with cosine similarity search
- MongoDB retrieval methods for incident history
- Streamlit RAG testing page with adjustable thresholds
- Agent integration showing similar incidents in console output

#### Performance
- Search speed: ~0.2 seconds for 1000+ embeddings
- Accuracy: 98-100% similarity for recurring patterns
- Storage: ~6KB per incident embedding

#### What We Learned
- **Pattern Recognition**: RAG immediately identified recurring Somerset Levels incidents (100% similarity)
- **Self-Improving**: Knowledge base grows automatically with each incident
- **Limitations Identified**: RAG finds similar events but can't explain *why* they're similar or trace causality

#### Try It
```bash
# Test RAG similarity search
uv run python scripts/test_rag.py

# Interactive dashboard testing
uv run streamlit run streamlit_app.py
# Navigate to "Test RAG Semantic Search" section
```

---

### [v0.3] Rainfall Correlation & Multi-Cluster Incidents
**Released**: November 22, 2025  
**Status**: Complete

#### What We Added
- **Rainfall API integration** for meteorological context
- **Per-cluster rainfall correlation** (24-hour window)
- **Multi-incident generation** (one per spatial cluster)
- **Context-aware summaries** distinguishing flood vs hydrology incidents
- **Scientific accuracy improvements** (acknowledged 48-72h catchment lag)

#### Technical Implementation
- `RainfallClient` with location-based search
- `calculate_total_rainfall()` method for cluster analysis
- Enhanced `generate_incident_node()` to process multiple clusters
- Rainfall statistics in console output

#### What We Learned
- **Domain Knowledge Matters**: River levels can lag rainfall by 48-72 hours
- **Context is Critical**: "No rainfall in 24h" is significant but incomplete
- **Self-Aware Reasoning**: Agent identifies its own limitations (24h window)

#### Example Output
```
Rainfall: 0mm in last 24h → investigate non-meteorological causes
Caveat: River levels can lag 48-72h behind rainfall events
```

---

### [v0.2] Spatial Clustering & Permit Integration
**Released**: November 21, 2025  
**Status**: Complete

#### What We Added
- **Spatial clustering** (10km radius using Haversine distance)
- **Temporal filtering** (24-hour window)
- **Public Registers API** integration for environmental permits
- **Per-cluster permit search** (1km radius)
- **Coordinate enrichment** from station metadata repository

#### Technical Implementation
- `cluster_anomalies_spatially()` algorithm
- `PublicRegistersClient` with coordinate-based search
- `StationMetadataRepository` for lat/lon enrichment
- Enhanced Streamlit dashboard with permit markers

#### What We Learned
- **Clustering Reduces Noise**: 76 anomalies → 5 localized incidents
- **Permits Provide Context**: Wessex Water discharge permits explain Somerset Levels pattern
- **Geocoding is Essential**: Postcode → lat/lon enables permit visualization

#### Example Output
```
Cluster 1: 5 anomalies near (53.85, -1.15)
Found 10 nearby permits including 3 Wessex Water discharge permits
```

---

### [v0.1] Basic Agentic Workflow
**Released**: November 20, 2025  
**Status**: Complete

#### What We Built
- **LangGraph agent** with autonomous decision-making
- **Multi-source data collection** (Flood + Hydrology APIs)
- **Threshold-based anomaly detection** (configurable)
- **MongoDB storage** for incidents
- **Streamlit dashboard** with interactive maps
- **MCP tools architecture** for API integration

#### Technical Implementation
- `AgentState` with message reduction for token efficiency
- `ToolNode` with async execution
- Conditional routing based on agent decisions
- Docker Compose infrastructure (MongoDB, PostgreSQL)

#### What We Learned
- **Agents Work**: LLM successfully chooses tools based on context
- **Tool Calling is Reliable**: GPT-4 correctly invokes MCP tools
- **Message Management Matters**: Token bloat requires trimming strategies

#### Example Flow
```
Agent → get_flood_readings → detect_anomalies → 
search_public_registers → generate_incident → store
```

---

## Upcoming Features

### Knowledge Graphs for Causal Reasoning 🔄
**Status**: Planned (Next)  
**Target**: December 2025

#### What We'll Add
- **Neo4j integration** for graph storage
- **Causal relationship modeling** (incident → cause → resolution)
- **Multi-hop queries** ("Which permits caused this via discharge?")
- **Hybrid RAG + Graph approach** (similarity + causality)
- **Hallucination prevention** ("Does this relationship actually exist?")

#### Why It Matters
RAG finds *similar* incidents. Graphs explain *why* incidents occur.

**RAG Question**: "Find similar flood events"  
**Graph Question**: "What caused this flood event?"

**RAG Limitation**: Can't answer "Did rainfall AND discharge cause this?"  
**Graph Solution**: Traverse edges to find causal chains

#### Technical Approach
- Neo4j graph database with Cypher queries
- `EnvironmentalGraphRepository` for graph operations
- Hybrid queries combining vector search + graph traversal
- Dashboard comparison: RAG vs Graph results side-by-side

#### Success Metrics
- Multi-hop queries working (3+ hops)
- Causal chain visualization
- Reduced false positives via relationship verification
- Blog post demonstrating 5 RAG failure modes

---

### Multi-Agent Collaboration 📅
**Status**: Planned  
**Target**: January 2026

#### Concept
Split monolithic agent into specialist roles:
- **FloodAnalystAgent**: Water levels, river flows
- **HydrologyAgent**: Groundwater, contamination
- **ComplianceAgent**: Permit violations
- **CoordinatorAgent**: Orchestrates specialists

#### Why It Matters
Specialist agents with focused prompts provide deeper analysis than one generalist.

---

### Predictive Intelligence 📅
**Status**: Planned  
**Target**: February 2026

#### Concept
- Met Office API for weather forecasts
- Predict floods 12-24 hours in advance
- Historical pattern matching
- Confidence scoring

#### Why It Matters
Shift from reactive (detecting floods) to proactive (preventing damage).

---

## Development Metrics

### Code Growth
| Phase | Total Lines | New Lines | Files Changed |
|-------|------------|-----------|---------------|
| v0.1 (Basic Agent) | 800 | 800 | 15 |
| v0.2 (Clustering) | 1,000 | +200 | 8 |
| v0.3 (Rainfall) | 1,120 | +120 | 6 |
| RAG (Nov 2025) | 1,270 | +150 | 5 |

### Test Coverage
| Phase | Test Scripts | Unit Tests | Integration Tests |
|-------|-------------|------------|-------------------|
| v0.1 | 5 | 1 | 4 |
| v0.2 | 6 | 1 | 5 |
| v0.3 | 7 | 1 | 6 |
| RAG | 8 | 1 | 7 |

### Documentation
| Phase | Blog Posts | README Updates | API Docs |
|-------|-----------|----------------|----------|
| v0.1 | 0 | 1 | 1 |
| v0.2 | 0 | 2 | 1 |
| v0.3 | 1 (LinkedIn) | 3 | 1 |
| RAG | 2 | 4 | 2 |

---

## Design Decisions

### Why pgvector Instead of Standalone Vector DB?

**Decision**: Use PostgreSQL + pgvector  
**Alternatives Considered**: Pinecone, Weaviate, Qdrant

**Reasoning**:
- Already using PostgreSQL for structured data
- Avoid operational complexity of separate vector DB
- pgvector performance adequate for POC scale (<10K incidents)
- Easier local development (one Docker Compose)

**Trade-offs**:
- Scaling limitation (pgvector slower at >1M vectors)
- Fewer vector-specific features
- Acceptable for proof-of-concept

---

### Why Threshold Detection Instead of Z-Score?

**Decision**: Simple threshold (value > 3.0m)  
**Alternatives Considered**: Z-score, Isolation Forest, LSTM

**Reasoning**:
- Domain experts use thresholds (flood alerts at fixed levels)
- Interpretable: "3.0m is flood risk level"
- Fast: O(n) single pass
- Z-score requires historical distribution (cold start problem)

**Trade-offs**:
- Less sophisticated than statistical methods
- Misses subtle anomalies
- Fixed threshold doesn't adapt to seasonal variations

**Future**: Hybrid approach (threshold for critical + z-score for subtle)

---

### Why LangGraph Instead of Simple Chains?

**Decision**: LangGraph with conditional routing  
**Alternatives Considered**: LangChain chains, plain Python

**Reasoning**:
- Agent needs to make decisions (fetch permits? check rainfall?)
- Conditional logic based on findings
- State management across steps
- Visibility into agent reasoning

**Trade-offs**:
- More complex than linear chains
- Higher token usage (conversation history)
- Learning curve for contributors

**Benefit**: Adaptive behavior worth the complexity

---

## Lessons Learned

### What Worked Well

1. **Iterative Development**: Small, testable increments
2. **Real Data First**: Using actual EA APIs from day one
3. **Documentation as Code**: Blog posts written alongside features
4. **Agent Autonomy**: LLM decision-making worked better than expected
5. **Public Data**: Government APIs are comprehensive and reliable

### What We'd Do Differently

1. **Test Coverage Earlier**: Should have added unit tests from v0.1
2. **Type Safety**: MyPy errors accumulated (25 current errors)
3. **Logging vs Prints**: Print statements everywhere, should use structured logging
4. **Clustering Algorithm**: Naive O(n²) implementation doesn't scale
5. **Error Handling**: Too many bare `except Exception` blocks

### Surprises

1. **RAG Works Immediately**: 98-100% matches on first try
2. **Agent Reasoning**: LLM correctly identifies data gaps
3. **API Reliability**: EA APIs very stable (>99% uptime observed)
4. **Geocoding Quality**: postcodes.io accurate for permit locations
5. **Community Interest**: LinkedIn engagement higher than expected

---

## Community & Feedback

### LinkedIn Engagement (Nov 2025)
- **Initial Post**: 250+ views, 15 comments
- **RAG Announcement**: 180+ views, 12 comments
- **Top Question**: "How does this compare to traditional monitoring?"
- **Interest Areas**: RAG implementation, knowledge graphs, public API usage

### GitHub Activity
- **Stars**: 8 (as of Nov 23, 2025)
- **Forks**: 2
- **Issues**: 3 open (feature requests)
- **Contributors**: 1 (author)

### Feature Requests
1. Air quality monitoring integration
2. Mobile app for field teams
3. Email/SMS alerting
4. Historical trend analysis dashboard

---

## Roadmap Timeline

```
Nov 2025: ✅ RAG (Semantic Search)
Dec 2025: 🔄 Knowledge Graphs (Causal Reasoning)
Jan 2026: 📅 Multi-Agent Collaboration
Feb 2026: 📅 Predictive Intelligence
Mar 2026: 📅 Cross-Domain Impact Analysis
```

---

## Following Along

**Want to track progress?**
- **GitHub**: Watch the [repository](https://github.com/steve-dickinson/agentic-environmental-intelligence)
- **LinkedIn**: Follow [@steve-dickinson](https://github.com/steve-dickinson) for updates
- **Blog**: Check [blog_posts/](../blog_posts/) for detailed write-ups
- **Changelog**: This page updated with each release

**Contributing**:
- Knowledge Graphs - actively seeking collaborators
- Domain expertise (hydrology, environmental science) welcome
- Neo4j/graph database experience helpful

---

*Last Updated: November 23, 2025*  
*Next Update: Knowledge Graphs release (Dec 2025)*
