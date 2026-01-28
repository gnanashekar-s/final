"""Spec generator node for creating technical specifications from stories."""
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import ApprovalStatus, WorkflowStage, WorkflowState
from app.config import settings
# from app.core.langfuse_client import observe


SPEC_SYSTEM_PROMPT = """You are an expert software architect specializing in FastAPI applications.
Your task is to create detailed technical specifications from user stories.

Each Specification should include:
1. Functional requirements
2. API endpoint designs (method, path, request/response schemas)
3. Data model definitions (SQLAlchemy models)
4. Security requirements (authentication, authorization)
5. Test plan with specific test cases

Focus ONLY on FastAPI backend development.
Output must be valid JSON."""


# @observe(name="spec_generator_node")
async def spec_generator_node(state: WorkflowState) -> dict[str, Any]:
    """
    Generate technical specifications from approved stories.
    """
    stories = state.get("stories", [])
    epics = state.get("epics", [])
    research = state.get("research_artifact", {})
    user_feedback = state.get("user_feedback", "")

    # Filter to approved stories only
    approved_stories = [
        s for s in stories
        if s.get("status") == ApprovalStatus.APPROVED.value
    ]

    if not approved_stories:
        return {
            "error_message": "No approved stories to generate specs from",
            "current_stage": WorkflowStage.FAILED,
        }

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.3,
        api_key=settings.openai_api_key,
    )

    # Build context
    epic_context = "\n".join([
        f"- {e['title']}: {e['goal']}"
        for e in epics if e.get("status") == ApprovalStatus.APPROVED.value
    ])

    research_context = ""
    if research:
        findings = research.get("findings", {})
        research_context = f"""
Technology Stack:
- Technologies: {', '.join(findings.get('key_technologies', ['FastAPI', 'SQLAlchemy', 'PostgreSQL']))}
- Patterns: {', '.join(findings.get('architecture_patterns', ['Clean Architecture']))}
"""

    all_specs = []

    for story in approved_stories:
        feedback_context = ""
        if user_feedback:
            feedback_context = f"\n\nPrevious feedback to address:\n{user_feedback}"

        prompt = f"""Create a detailed Technical Specification for this User Story:

Story: {story['title']}
Description: {story['description']}
Acceptance Criteria:
{json.dumps(story.get('acceptance_criteria', []), indent=2)}
Edge Cases: {', '.join(story.get('edge_cases', []))}
Technical Notes: {story.get('technical_notes', 'None')}

Context:
Epics: {epic_context}
{research_context}
{feedback_context}

Return a JSON object with this structure:
{{
    "content": "Full specification document in markdown format",
    "requirements": {{
        "functional": ["List of functional requirements"],
        "non_functional": ["Performance", "Scalability", "Security requirements"]
    }},
    "api_design": {{
        "endpoints": [
            {{
                "method": "POST",
                "path": "/api/v1/resource",
                "description": "Create a resource",
                "request_body": {{"field": "type"}},
                "response": {{"field": "type"}},
                "status_codes": [201, 400, 401],
                "auth_required": true
            }}
        ]
    }},
    "data_model": {{
        "models": [
            {{
                "name": "ModelName",
                "table": "table_name",
                "fields": [
                    {{"name": "id", "type": "Integer", "primary_key": true}},
                    {{"name": "name", "type": "String(255)", "nullable": false}}
                ],
                "relationships": ["other_model"]
            }}
        ]
    }},
    "security_requirements": {{
        "authentication": "JWT Bearer token",
        "authorization": ["Role-based access"],
        "input_validation": ["Pydantic schemas"],
        "data_protection": ["Password hashing"]
    }},
    "test_plan": {{
        "unit_tests": ["List of unit test cases"],
        "integration_tests": ["List of integration test cases"],
        "edge_case_tests": ["Tests for edge cases"]
    }}
}}"""

        response = await llm.ainvoke([
            SystemMessage(content=SPEC_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        # Parse response
        try:
            spec_data = json.loads(response.content)
        except json.JSONDecodeError:
            content = response.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    spec_data = json.loads(content[start:end])
                except json.JSONDecodeError:
                    spec_data = {"content": response.content}

        # Generate Mermaid diagrams
        # mermaid_diagrams = await generate_spec_diagrams(spec_data)
        #::fix-me

        all_specs.append({
            "id": None,
            "story_index": stories.index(story),
            "story_title": story["title"],
            "content": spec_data.get("content", ""),
            "requirements": spec_data.get("requirements", {}),
            "api_design": spec_data.get("api_design", {}),
            "data_model": spec_data.get("data_model", {}),
            "security_requirements": spec_data.get("security_requirements", {}),
            "test_plan": spec_data.get("test_plan", {}),
            "mermaid_diagrams": mermaid_diagrams,
            "status": ApprovalStatus.PENDING.value,
            "feedback": None,
        })

    return {
        "specs": all_specs,
        "current_stage": WorkflowStage.SPEC_REVIEW,
        "awaiting_approval": True,
        "approval_type": "spec",
        "approval_ids": list(range(len(all_specs))),
        "user_feedback": None,
    }


# async def generate_spec_diagrams(spec_data: dict) -> dict[str, str]:
#     """Generate Mermaid diagrams for the specification."""
#     diagrams = {}

#     # Generate API sequence diagram
#     api_design = spec_data.get("api_design", {})
#     endpoints = api_design.get("endpoints", [])

#     if endpoints:
#         lines = ["sequenceDiagram", "    participant C as Client", "    participant A as API", "    participant D as Database"]
#         for ep in endpoints[:5]:  # Limit to 5 endpoints
#             method = ep.get("method", "GET")
#             path = ep.get("path", "/")
#             desc = ep.get("description", "")[:30]
#             lines.append(f"    C->>A: {method} {path}")
#             if ep.get("auth_required"):
#                 lines.append("    A->>A: Validate JWT")
#             lines.append("    A->>D: Query/Update")
#             lines.append("    D-->>A: Result")
#             lines.append(f"    A-->>C: {ep.get('status_codes', [200])[0]} Response")
#         diagrams["api_sequence"] = "\n".join(lines)

#     # Generate data model ER diagram
#     data_model = spec_data.get("data_model", {})
#     models = data_model.get("models", [])

#     if models:
#         lines = ["erDiagram"]
#         for model in models:
#             name = model.get("name", "Model")
#             lines.append(f"    {name} {{")
#             for field in model.get("fields", [])[:10]:
#                 field_name = field.get("name", "field")
#                 field_type = field.get("type", "String")
#                 pk = " PK" if field.get("primary_key") else ""
#                 lines.append(f"        {field_type} {field_name}{pk}")
#             lines.append("    }")

#         # Add relationships
#         for model in models:
#             for rel in model.get("relationships", []):
#                 lines.append(f"    {model['name']} ||--o{{ {rel} : has")

#         diagrams["data_model"] = "\n".join(lines)

#     return diagrams


async def process_spec_approval(state: WorkflowState) -> dict[str, Any]:
    """Process spec approval/rejection from user."""
    specs = state.get("specs", [])

    all_approved = all(
        spec.get("status") == ApprovalStatus.APPROVED.value
        for spec in specs
    )

    if all_approved:
        return {
            "awaiting_approval": False,
            "current_stage": WorkflowStage.CODE_GENERATION,
        }

    rejected = [
        spec for spec in specs
        if spec.get("status") == ApprovalStatus.REJECTED.value
    ]

    if rejected:
        feedback = "\n".join([
            f"- {spec['story_title']}: {spec.get('feedback', 'No specific feedback')}"
            for spec in rejected
        ])
        return {
            "user_feedback": feedback,
            "current_stage": WorkflowStage.SPEC_GENERATION,
            "awaiting_approval": False,
        }

    return {"awaiting_approval": True}
