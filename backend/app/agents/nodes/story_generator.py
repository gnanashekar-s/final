"""Story generator node for creating user stories from epics."""
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import ApprovalStatus, WorkflowStage, WorkflowState
from app.config import settings
# from app.core.langfuse_client import observe


STORY_SYSTEM_PROMPT = """You are an expert agile coach and technical writer.
Your task is to create detailed user stories from Epics.

Each User Story should:
1. Follow the format: "As a [role], I want [feature], so that [benefit]"
2. Have clear, testable acceptance criteria in Given-When-Then format
3. Identify edge cases and error scenarios
4. Be sized for 1-5 days of development work
5. Focus on FastAPI backend functionality

Output must be valid JSON."""


# @observe(name="story_generator_node")
async def story_generator_node(state: WorkflowState) -> dict[str, Any]:
    """
    Generate user stories from approved epics.
    """
    epics = state.get("epics", [])
    product_request = state.get("product_request", "")
    user_feedback = state.get("user_feedback", "")

    # Filter to approved epics only
    approved_epics = [
        e for e in epics
        if e.get("status") == ApprovalStatus.APPROVED.value
    ]

    if not approved_epics:
        return {
            "error_message": "No approved epics to generate stories from",
            "current_stage": WorkflowStage.FAILED,
        }

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.4,
        api_key=settings.openai_api_key,
    )

    all_stories = []

    for epic in approved_epics:
        feedback_context = ""
        if user_feedback:
            feedback_context = f"\n\nPrevious feedback to address:\n{user_feedback}"

        prompt = f"""Create User Stories for this Epic:

Epic: {epic['title']}
Goal: {epic['goal']}
Scope: {epic['scope']}
Priority: {epic.get('priority', 'medium')}

Context - Original Product Request: {product_request}
{feedback_context}

Generate 2-5 User Stories that fully implement this Epic.
Focus ONLY on FastAPI backend functionality.

Return a JSON object with this structure:
{{
    "stories": [
        {{
            "title": "Story title",
            "description": "As a [role], I want [feature], so that [benefit]",
            "acceptance_criteria": [
                {{
                    "given": "Initial context",
                    "when": "Action taken",
                    "then": "Expected result"
                }}
            ],
            "priority": "high|medium|low",
            "story_points": 3,  // 1, 2, 3, 5, or 8
            "edge_cases": ["Edge case 1", "Edge case 2"],
            "technical_notes": "Implementation hints"
        }}
    ]
}}

Ensure stories:
1. Are independently testable
2. Cover both happy path and error cases
3. Include API endpoint definitions where applicable
4. Consider authentication/authorization requirements"""

        response = await llm.ainvoke([
            SystemMessage(content=STORY_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        # Parse response
        try:
            data = json.loads(response.content)
            stories_data = data.get("stories", [])
            # print(stories_data)
        except json.JSONDecodeError:
            content = response.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    data = json.loads(content[start:end])
                    stories_data = data.get("stories", [])
                except json.JSONDecodeError:
                    stories_data = []

        # Convert to internal format
        for i, story in enumerate(stories_data):
            all_stories.append({
                "id": None,
                "epic_index": epic["index"],
                "epic_title": epic["title"],
                "title": story.get("title", f"Story {len(all_stories) + 1}"),
                "description": story.get("description", ""),
                "acceptance_criteria": story.get("acceptance_criteria", []),
                "priority": story.get("priority", "medium"),
                "story_points": story.get("story_points"),
                "edge_cases": story.get("edge_cases", []),
                "technical_notes": story.get("technical_notes", ""),
                "status": ApprovalStatus.PENDING.value,
                "feedback": None,
            })

    return {
        "stories": all_stories,
        "current_stage": WorkflowStage.STORY_REVIEW,
        "awaiting_approval": True,
        "approval_type": "story",
        "approval_ids": list(range(len(all_stories))),
        "user_feedback": None,
    }


async def process_story_approval(state: WorkflowState) -> dict[str, Any]:
    """Process story approval/rejection from user."""
    stories = state.get("stories", [])

    # Check if all stories are approved
    all_approved = all(
        story.get("status") == ApprovalStatus.APPROVED.value
        for story in stories
    )

    if all_approved:
        return {
            "awaiting_approval": False,
            "current_stage": WorkflowStage.SPEC_GENERATION,
        }

    # Check for rejections with feedback
    rejected = [
        story for story in stories
        if story.get("status") == ApprovalStatus.REJECTED.value
    ]

    if rejected:
        feedback = "\n".join([
            f"- {story['title']}: {story.get('feedback', 'No specific feedback')}"
            for story in rejected
        ])
        return {
            "user_feedback": feedback,
            "current_stage": WorkflowStage.STORY_GENERATION,
            "awaiting_approval": False,
        }

    return {"awaiting_approval": True}


# @observe(name="estimate_stories")
async def estimate_stories(stories: list[dict]) -> list[dict]:
    """
    Estimate story points for stories that don't have them.
    """
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.2,
        api_key=settings.openai_api_key,
    )

    stories_without_points = [
        s for s in stories if not s.get("story_points")
    ]

    if not stories_without_points:
        return stories

    prompt = f"""Estimate story points for these user stories using Fibonacci scale (1, 2, 3, 5, 8):

{json.dumps(stories_without_points, indent=2)}

Return a JSON array with objects containing "title" and "story_points" for each story.
Consider:
- 1 point: trivial changes, config updates
- 2 points: simple features, basic CRUD
- 3 points: moderate complexity, some logic
- 5 points: complex features, integrations
- 8 points: very complex, should consider splitting"""

    response = await llm.ainvoke([
        SystemMessage(content="You are an agile estimation expert."),
        HumanMessage(content=prompt),
    ])

    try:
        estimates = json.loads(response.content)
        estimate_map = {e["title"]: e["story_points"] for e in estimates}

        for story in stories:
            if not story.get("story_points"):
                story["story_points"] = estimate_map.get(story["title"], 3)
    except (json.JSONDecodeError, KeyError):
        # Default to 3 points if estimation fails
        for story in stories:
            if not story.get("story_points"):
                story["story_points"] = 3

    return stories
