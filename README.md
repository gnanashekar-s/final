# Multi-Agent Product-to-Code System

A production-grade multi-agent system that transforms Product Requests into working FastAPI code through a series of AI-powered stages: Epics → User Stories → Specs → Working Code with validation.

## Features

- **Multi-Agent Workflow**: LangGraph-powered workflow with specialized agents for each stage
- **Human-in-the-Loop (HITL)**: Approval gates for epics, stories, and specs
- **Real-time Updates**: Server-Sent Events (SSE) for live progress tracking
- **Code Generation**: FastAPI-only code generation with validation
- **Observability**: Langfuse integration for tracing and monitoring
- **Role-based Access**: JWT authentication with User/Admin roles

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Agents**: LangGraph with checkpointing
- **LLM**: OpenAI GPT-4.1
- **Web Search**: OpenAI Web Search / Tavily
- **UI**: Streamlit (Multi-page with sidebar navigation)
- **Real-time**: Server-Sent Events (SSE)
- **Observability**: Langfuse
- **Containerization**: Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key
- (Optional) Langfuse account for observability
- (Optional) Tavily API key for web search

### Setup

1. Clone the repository:
   ```bash
   cd /home/harizibam/shekar/final
   ```

2. Copy the environment file and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start Streamlit
streamlit run app.py
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings & env vars
│   │   ├── database.py          # DB connection
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── api/                 # API routes
│   │   ├── services/            # Business logic
│   │   ├── agents/              # LangGraph agents
│   │   │   ├── graph.py         # Main workflow
│   │   │   ├── state.py         # Shared state
│   │   │   ├── nodes/           # Agent nodes
│   │   │   └── tools/           # Agent tools
│   │   └── core/                # Utilities
│   ├── alembic/                 # DB migrations
│   └── tests/
├── frontend/
│   ├── app.py                   # Streamlit main
│   ├── pages/                   # Multi-page navigation
│   └── components/              # Reusable components
├── docker-compose.yml
└── README.md
```

## Workflow Stages

```
START → Research → Epic Generation ↔ [HITL Review]
      → Story Generation ↔ [HITL Review]
      → Spec Generation ↔ [HITL Review]
      → Code Generation → Validation ↔ [Auto-fix] → END
```

### 1. Research Phase
- Web search for relevant technical information
- Best practices and patterns discovery
- Technology recommendations

### 2. Epic Generation
- Break down product request into high-level epics
- Dependency mapping between epics
- Mermaid diagram generation

### 3. Story Generation
- Create user stories for each epic
- Acceptance criteria (Given-When-Then)
- Edge case identification
- Story point estimation

### 4. Spec Generation
- Detailed technical specifications
- API endpoint design
- Data model definitions
- Security requirements
- Test plans

### 5. Code Generation
- FastAPI backend code generation
- SQLAlchemy models
- Pydantic schemas
- Test files
- Requirements.txt

### 6. Validation
- Syntax validation
- Lint checking (ruff)
- Pattern validation
- Auto-fix loop for errors

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get token
- `GET /api/v1/auth/me` - Get current user

### Projects
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `POST /api/v1/projects/{id}/runs` - Start workflow

### Epics, Stories, Specs, Code
- CRUD operations for each artifact type
- Approval endpoints for HITL gates

### Streaming
- `GET /api/v1/stream/{run_id}` - SSE endpoint for real-time updates

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `JWT_SECRET` | Secret key for JWT tokens | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | No |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | No |
| `TAVILY_API_KEY` | Tavily API key for web search | No |
| `DEBUG` | Enable debug mode | No |

## Testing

```bash
cd backend
pytest tests/ -v
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License
