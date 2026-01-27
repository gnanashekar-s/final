"""Research node for gathering information about the product request."""
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import WorkflowStage, WorkflowState
from app.agents.tools.web_search import web_search
from app.config import settings
from app.core.langfuse_client import observe


RESEARCH_SYSTEM_PROMPT = """You are a technical research agent specialized in software engineering.
Your task is to research and gather relevant information for building a software product.

Given a product request, you will:
1. Identify key technical concepts and requirements
2. Search for relevant best practices and patterns
3. Find documentation for technologies that might be needed
4. Summarize findings in a structured format

Always focus on FastAPI backend development patterns and best practices.
Output your findings in a structured JSON format."""


@observe(name="research_node")
async def research_node(state: WorkflowState) -> dict[str, Any]:
    """
    Research node that gathers information about the product request.
    Uses web search to find relevant documentation and best practices.
    """
    product_request = state.get("product_request", "")
    constraints = state.get("constraints", "")

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.3,
        api_key=settings.openai_api_key,
    )

    # Generate search queries based on product request
    query_prompt = f"""Based on this product request, generate 3-5 targeted search queries
to find relevant technical information:

Product Request: {product_request}
{f'Constraints: {constraints}' if constraints else ''}

Return a JSON object with a "queries" array of search query strings.
Focus on:
- FastAPI patterns and best practices
- Database design for this use case
- Security considerations
- Similar project architectures"""

    query_response = await llm.ainvoke([
        SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
        HumanMessage(content=query_prompt),
    ])

    # Parse queries
    try:
        queries_data = json.loads(query_response.content)
        queries = queries_data.get("queries", [])
    except json.JSONDecodeError:
        # Fallback queries
        queries = [
            f"FastAPI {product_request[:50]} best practices",
            "FastAPI SQLAlchemy project structure",
            "FastAPI authentication patterns",
        ]

    # Execute searches
    all_results = []
    for query in queries[:5]:  # Limit to 5 queries
        try:
            results = await web_search.ainvoke({"query": query, "max_results": 3})
            all_results.extend(results)
        except Exception as e:
            print(f"Search failed for query '{query}': {e}")

    # Summarize findings
    summary_prompt = f"""Based on these search results, create a comprehensive research summary
for building the following product:

Product Request: {product_request}

Search Results:
{json.dumps(all_results, indent=2)}

Provide a structured JSON response with:
{{
    "key_technologies": ["list of recommended technologies"],
    "architecture_patterns": ["recommended patterns"],
    "security_considerations": ["security items to address"],
    "data_model_hints": ["suggested data entities"],
    "api_design_hints": ["API design recommendations"],
    "summary": "brief summary of findings"
}}"""

    summary_response = await llm.ainvoke([
        SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
        HumanMessage(content=summary_prompt),
    ])

    # Parse summary
    try:
        findings = json.loads(summary_response.content)
    except json.JSONDecodeError:
        findings = {
            "key_technologies": ["FastAPI", "SQLAlchemy", "PostgreSQL", "Pydantic"],
            "architecture_patterns": ["Clean Architecture", "Repository Pattern"],
            "security_considerations": ["JWT Authentication", "Input Validation"],
            "data_model_hints": [],
            "api_design_hints": ["RESTful API design"],
            "summary": summary_response.content,
        }

    # Build research artifact
    research_artifact = {
        "urls": [r.get("url", "") for r in all_results if r.get("url")],
        "findings": findings,
        "summary": findings.get("summary", ""),
        "queries": queries,
    }

    return {
        "research_queries": queries,
        "research_artifact": research_artifact,
        "current_stage": WorkflowStage.EPIC_GENERATION,
    }


async def should_continue_research(state: WorkflowState) -> str:
    """Determine if more research is needed."""
    artifact = state.get("research_artifact")

    if not artifact or not artifact.get("findings"):
        retry_count = state.get("retry_count", 0)
        if retry_count < state.get("max_retries", 3):
            return "retry"
        return "fail"

    return "continue"
