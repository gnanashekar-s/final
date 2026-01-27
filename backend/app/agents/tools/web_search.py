"""Web search tool using OpenAI's web search or Tavily."""
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.config import settings


class WebSearchInput(BaseModel):
    """Input for web search tool."""
    query: str = Field(description="The search query")
    max_results: int = Field(default=5, description="Maximum number of results to return")


class WebSearchResult(BaseModel):
    """Result from web search."""
    title: str
    url: str
    snippet: str


@tool
async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for information related to a query.
    Returns a list of search results with titles, URLs, and snippets.

    Args:
        query: The search query
        max_results: Maximum number of results to return (default 5)

    Returns:
        List of search results
    """
    results = []

    # Try Tavily first if available
    if settings.tavily_api_key:
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=settings.tavily_api_key)
            response = client.search(query, max_results=max_results)

            for result in response.get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", ""),
                })
            return results
        except Exception as e:
            print(f"Tavily search failed: {e}")

    # Fallback to OpenAI web search via function calling
    if settings.openai_api_key:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)

            # Use GPT-4 with web browsing capability
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that searches the web for information. Return search results as JSON.",
                    },
                    {
                        "role": "user",
                        "content": f"Search the web for: {query}. Return {max_results} relevant results with title, url, and snippet for each.",
                    },
                ],
                response_format={"type": "json_object"},
            )

            import json

            content = response.choices[0].message.content
            data = json.loads(content)

            for result in data.get("results", [])[:max_results]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", result.get("content", "")),
                })
            return results
        except Exception as e:
            print(f"OpenAI web search failed: {e}")

    return results


@tool
async def search_technical_docs(query: str, technology: str) -> list[dict]:
    """
    Search for technical documentation for a specific technology.

    Args:
        query: The search query
        technology: The technology to search docs for (e.g., 'fastapi', 'sqlalchemy')

    Returns:
        List of documentation search results
    """
    # Construct targeted search query
    search_query = f"{technology} documentation {query}"
    return await web_search.ainvoke({"query": search_query, "max_results": 5})


@tool
async def search_best_practices(topic: str) -> list[dict]:
    """
    Search for best practices and patterns for a given topic.

    Args:
        topic: The topic to search best practices for

    Returns:
        List of best practice resources
    """
    search_query = f"best practices {topic} software development 2024"
    return await web_search.ainvoke({"query": search_query, "max_results": 5})


# Export tools
web_search_tools = [web_search, search_technical_docs, search_best_practices]
