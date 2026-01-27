# Backend Setup & Testing Guide

This guide walks you through setting up and testing the Product-to-Code workflow system.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (for PostgreSQL and Langfuse)
- OpenAI API key

## Quick Start

### 1. Environment Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `backend/.env` and set:

```bash
# REQUIRED - Get from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-actual-openai-key

# OPTIONAL but recommended - better web search results
# Get from https://tavily.com
TAVILY_API_KEY=tvly-your-key
```

### 3. Start Database (Optional for CLI testing)

For full API testing, start PostgreSQL:

```bash
# From project root
docker-compose up -d postgres
```

For CLI workflow testing, you can skip the database.

## Testing the Workflow

### Option A: Simple Test Script (Recommended First)

Test individual nodes and full workflow:

```bash
cd backend

# Run all tests
python test_workflow.py

# Test only research node
python test_workflow.py research

# Test only epic generation
python test_workflow.py epic

# Test full workflow with HITL pause
python test_workflow.py workflow
```

### Option B: Interactive CLI Runner

Test the complete workflow with interactive approvals:

```bash
cd backend

# Interactive mode (prompts for approval at each stage)
python run_workflow.py "Build a REST API for managing TODO items with user auth"

# Auto-approve mode (for quick testing)
python run_workflow.py --auto-approve "Build a REST API for managing TODO items"

# With constraints
python run_workflow.py -c "Use PostgreSQL and Redis" "Build a REST API for managing TODO items"
```

### Option C: Full API Server

Start the FastAPI server and test via Swagger UI:

```bash
cd backend

# Start server
uvicorn app.main:app --reload

# Open browser to http://localhost:8000/docs
```

## Setting Up Langfuse (Local Observability)

Langfuse provides tracing and monitoring for your LLM calls.

### 1. Start Langfuse

```bash
# From project root
docker-compose -f langfuse/docker-compose.yml up -d

# Wait for it to start (check logs)
docker-compose -f langfuse/docker-compose.yml logs -f
```

### 2. Create Account and API Keys

1. Open http://localhost:3000
2. Create a new account
3. Go to **Settings** > **API Keys**
4. Click **Create API Key**
5. Copy the **Public Key** and **Secret Key**

### 3. Configure Backend

Edit `backend/.env`:

```bash
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_HOST=http://localhost:3000
```

### 4. View Traces

1. Run your workflow
2. Open http://localhost:3000
3. Go to **Traces** to see all LLM calls
4. Click on a trace to see details (input, output, tokens, latency)

## Understanding the Workflow

The workflow progresses through these stages:

```
RESEARCH
    ↓
EPIC_GENERATION → EPIC_REVIEW (HITL pause)
    ↓ (after approval)
STORY_GENERATION → STORY_REVIEW (HITL pause)
    ↓ (after approval)
SPEC_GENERATION → SPEC_REVIEW (HITL pause)
    ↓ (after approval)
CODE_GENERATION
    ↓
VALIDATION ↔ AUTO_FIX (loop up to 3 times)
    ↓
COMPLETED or FAILED
```

### HITL (Human-in-the-Loop) Gates

At each review stage, the workflow pauses and waits for approval:
- **Approve**: Continue to the next stage
- **Reject with Feedback**: Regenerate with your feedback incorporated

## Workflow Logging

The workflow outputs detailed logs to help you track progress:

```
============================================================
STARTING WORKFLOW - Run ID: 1
============================================================
Product Request: Build a simple REST API for managing TODO items...

============================================================
STAGE START: RESEARCH
============================================================
  → Starting agent: research
  ✓ Created 3 research URL(s)
  ← Agent research completed: Found 3 URLs
STAGE COMPLETED: RESEARCH
============================================================

============================================================
STAGE START: EPIC GENERATION
============================================================
  → Starting agent: epic_generator
  ✓ Created 4 epic(s)
    Epic 1: Core Infrastructure Setup
    Epic 2: User Authentication
    Epic 3: TODO Management API
    Epic 4: Testing & Documentation
  ⏸ Waiting for approval: epic IDs [0, 1, 2, 3]
STAGE COMPLETED: EPIC GENERATION
============================================================
```

## Troubleshooting

### "OPENAI_API_KEY not set"

Make sure your `.env` file has a valid OpenAI API key:
```bash
OPENAI_API_KEY=sk-...
```

### "Research failed" / No search results

This can happen if:
1. Your OpenAI API key doesn't have enough credits
2. Tavily API key is not set (falls back to OpenAI which may not have web search)

Try adding a Tavily API key for better search results:
```bash
TAVILY_API_KEY=tvly-...
```

### Langfuse connection errors

Make sure Langfuse is running:
```bash
docker-compose -f langfuse/docker-compose.yml ps
docker-compose -f langfuse/docker-compose.yml logs
```

If you don't want to use Langfuse, leave the keys empty in `.env` and the system will work without it.

### Import errors

Make sure you're in the virtual environment and dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Next Steps

Once the CLI workflow is working:

1. **Test the API endpoints**: Start the FastAPI server and test via Swagger UI
2. **Run database migrations**: `alembic upgrade head`
3. **Start the Streamlit frontend**: `cd frontend && streamlit run app.py`

## Files Reference

| File | Purpose |
|------|---------|
| `test_workflow.py` | Simple tests for individual nodes and workflow |
| `run_workflow.py` | Interactive CLI runner with approvals |
| `app/agents/graph.py` | Main LangGraph workflow definition |
| `app/agents/nodes/*.py` | Individual agent nodes |
| `app/agents/state.py` | Workflow state definition |
| `app/core/logging.py` | Logging configuration |
| `app/config.py` | Environment configuration |
