"""Epic generator node for creating epics from product request."""
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import ApprovalStatus, WorkflowStage, WorkflowState
from app.config import settings
from app.core.langfuse_client import observe


EPIC_SYSTEM_PROMPT = """You are an expert product manager and software architect.
Your task is to break down a product request into well-defined Epics.

Each Epic should:
1. Have a clear, actionable title
2. Define a specific goal
3. Outline the scope clearly
4. Identify dependencies on other epics
5. Be sized appropriately (not too large, not too small)

Focus on FastAPI backend development - no frontend epics.
Output must be valid JSON."""


@observe(name="epic_generator_node")
async def epic_generator_node(state: WorkflowState) -> dict[str, Any]:
    """
    Generate epics from the product request and research findings.
    """
    product_request = state.get("product_request", "")
    constraints = state.get("constraints", "")
    research = state.get("research_artifact", {})
    user_feedback = state.get("user_feedback", "")

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.4,
        api_key=settings.openai_api_key,
    )

    # Build context from research
    research_context = ""
    if research:
        findings = research.get("findings", {})
        research_context = f"""
Research Findings:
- Key Technologies: {', '.join(findings.get('key_technologies', []))}
- Architecture Patterns: {', '.join(findings.get('architecture_patterns', []))}
- Security Considerations: {', '.join(findings.get('security_considerations', []))}
- Data Model Hints: {', '.join(findings.get('data_model_hints', []))}
"""

    # Build feedback context
    feedback_context = ""
    if user_feedback:
        feedback_context = f"\n\nPrevious feedback to address:\n{user_feedback}"

    prompt = f"""Create a set of Epics for this product request:

Product Request: {product_request}
{f'Constraints: {constraints}' if constraints else ''}
{research_context}
{feedback_context}

Generate 3-7 Epics that cover the complete backend implementation.
Focus ONLY on FastAPI backend development - no frontend, mobile, or UI epics.

Return a JSON object with this structure:
{{
    "epics": [
        {{
            "title": "Epic title",
            "goal": "What this epic aims to achieve",
            "scope": "What's included and excluded",
            "priority": "critical|high|medium|low",
            "dependencies": [0, 1],  // indices of epics this depends on
            "estimated_stories": 3  // rough estimate of user stories
        }}
    ],
    "dependency_rationale": "Brief explanation of why dependencies are structured this way"
}}

Ensure epics are:
1. Independent where possible
2. Properly sequenced (core infrastructure first)
3. Focused on FastAPI patterns (routes, models, services, etc.)"""

    response = await llm.ainvoke([
        SystemMessage(content=EPIC_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    # Parse response
    try:
        data = json.loads(response.content)
        epics_data = data.get("epics", [])
    except json.JSONDecodeError:
        # Try to extract JSON from response
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(content[start:end])
                epics_data = data.get("epics", [])
            except json.JSONDecodeError:
                epics_data = []

    # Convert to internal format
    epics = []
    for i, epic in enumerate(epics_data):
        epics.append({
            "id": None,  # Will be assigned when saved
            "index": i,
            "title": epic.get("title", f"Epic {i + 1}"),
            "goal": epic.get("goal", ""),
            "scope": epic.get("scope", ""),
            "priority": epic.get("priority", "medium"),
            "dependencies": epic.get("dependencies", []),
            "status": ApprovalStatus.PENDING.value,
            "feedback": None,
        })

    # Generate Mermaid dependency diagram
    mermaid = await generate_epic_diagram(epics)

    return {
        "epics": epics,
        "epic_dependency_graph": mermaid,
        "current_stage": WorkflowStage.EPIC_REVIEW,
        "awaiting_approval": True,
        "approval_type": "epic",
        "approval_ids": list(range(len(epics))),
        "user_feedback": None,  # Clear feedback after processing
    }


async def generate_epic_diagram(epics: list[dict]) -> str:
    """Generate a Mermaid diagram for epic dependencies."""
    lines = ["graph TD"]

    for epic in epics:
        idx = epic["index"]
        title = epic["title"][:30].replace('"', "'")
        priority = epic.get("priority", "medium")

        # Add node with styling based on priority
        style = ""
        if priority == "critical":
            style = ":::critical"
        elif priority == "high":
            style = ":::high"

        lines.append(f'    E{idx}["{title}"]{style}')

    # Add dependencies
    for epic in epics:
        idx = epic["index"]
        for dep in epic.get("dependencies", []):
            if dep < len(epics):
                lines.append(f"    E{dep} --> E{idx}")

    # Add styling
    lines.extend([
        "",
        "    classDef critical fill:#ff6b6b,stroke:#c92a2a",
        "    classDef high fill:#ffd43b,stroke:#fab005",
    ])

    return "\n".join(lines)


async def process_epic_approval(state: WorkflowState) -> dict[str, Any]:
    """Process epic approval/rejection from user."""
    epics = state.get("epics", [])

    # Check if all epics are approved
    all_approved = all(
        epic.get("status") == ApprovalStatus.APPROVED.value
        for epic in epics
    )

    if all_approved:
        return {
            "awaiting_approval": False,
            "current_stage": WorkflowStage.STORY_GENERATION,
        }

    # Check for rejections with feedback
    rejected = [
        epic for epic in epics
        if epic.get("status") == ApprovalStatus.REJECTED.value
    ]

    if rejected:
        # Collect feedback for regeneration
        feedback = "\n".join([
            f"- {epic['title']}: {epic.get('feedback', 'No specific feedback')}"
            for epic in rejected
        ])
        return {
            "user_feedback": feedback,
            "current_stage": WorkflowStage.EPIC_GENERATION,
            "awaiting_approval": False,
        }

    # Still pending
    return {"awaiting_approval": True}
