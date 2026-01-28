"""Code generator node for creating FastAPI code from specs."""
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import WorkflowStage, WorkflowState
from app.agents.tools.code_tools import (
    check_fastapi_patterns,
    extract_imports,
    generate_requirements,
    validate_fastapi_only,
    validate_python_syntax,
)
from app.config import settings
# from app.core.langfuse_client import observe


CODE_SYSTEM_PROMPT = """You are an expert FastAPI developer.
Your task is to generate production-ready FastAPI backend code from technical specifications.

Code requirements:
1. Use FastAPI with async endpoints
2. Use SQLAlchemy 2.0+ with async support
3. Use Pydantic v2 for schemas
4. Implement proper error handling with HTTPException
5. Include dependency injection where appropriate
6. Follow Python best practices (type hints, docstrings)
7. Generate ONLY FastAPI backend code - NO frontend code

DO NOT generate:
- React, Vue, Angular, or any frontend code
- HTML templates
- Streamlit or Gradio code
- Flask or Django code

Output must be valid JSON with file contents."""


# @observe(name="code_generator_node")
async def code_generator_node(state: WorkflowState) -> dict[str, Any]:
    """
    Generate FastAPI code from approved specifications.
    """
    specs = state.get("specs", [])
    research = state.get("research_artifact", {})
    user_feedback = state.get("user_feedback", "")

    # Filter to approved specs
    approved_specs = [
        s for s in specs
        if s.get("status") == "approved"
    ]

    if not approved_specs:
        return {
            "error_message": "No approved specs to generate code from",
            "current_stage": WorkflowStage.FAILED,
        }

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.2,
        api_key=settings.openai_api_key,
    )

    # Aggregate all specs for comprehensive code generation
    all_endpoints = []
    all_models = []
    all_requirements = []
    all_tests = []

    for spec in approved_specs:
        api_design = spec.get("api_design", {})
        all_endpoints.extend(api_design.get("endpoints", []))

        data_model = spec.get("data_model", {})
        all_models.extend(data_model.get("models", []))

        requirements = spec.get("requirements", {})
        all_requirements.extend(requirements.get("functional", []))

        test_plan = spec.get("test_plan", {})
        all_tests.extend(test_plan.get("unit_tests", []))

    feedback_context = ""
    if user_feedback:
        feedback_context = f"\n\nPrevious feedback to address:\n{user_feedback}"

    prompt = f"""Generate a complete, runnable FastAPI backend based on the specifications below.

Specifications
API Endpoints:
{json.dumps(all_endpoints, indent=2)}

Data Models:
{json.dumps(all_models, indent=2)}

Requirements:
{json.dumps(all_requirements, indent=2)}

Test Cases:
{json.dumps(all_tests, indent=2)}
{feedback_context}

Primary goal (MANDATORY)
- Generate a project that runs without errors and implements the requested CRUD behavior end-to-end.
- Keep the design modular and easy to extend.

Architecture rules (MANDATORY)
- FastAPI with async endpoints.
- Pydantic v2 for request/response schemas.
- Clear separation of concerns:
  - routers = HTTP layer only (validation, status codes, dependencies)
  - services = business logic (no FastAPI imports)
  - storage/repository = data access layer
- Add type hints and docstrings for all public functions/classes.
- Implement consistent error handling (404 not found, 409 conflict if applicable, 422 validation via Pydantic).

Storage & dependencies (MANDATORY)
- Default to an IN-MEMORY implementation with the fewest dependencies possible.
- Implement BOTH in-memory structures:
  1) list-based store (array)
  2) dict-based store keyed by id
- Use a small repository abstraction so swapping storage later is easy.
- Only generate SQLAlchemy/database code IF the spec explicitly requires a real database. If not required, do NOT include SQLAlchemy or database setup files.

File structure (ADAPTIVE)
- Create only the files that are needed for this spec, but keep the code modular.
- Use this baseline structure and add one router/service per resource:

{{
  "files": {{
    "main.py": "FastAPI app entry point; registers routers; app startup",
    "schemas.py": "Pydantic v2 schemas (or split by resource if needed)",
    "dependencies.py": "FastAPI dependencies (repo/service wiring)",
    "storage.py": "In-memory repositories (list + dict) and base interfaces",
    "routers/__init__.py": "Router package init",
    "routers/[resource].py": "One router per resource; CRUD endpoints",
    "services/__init__.py": "Services package init",
    "services/[service].py": "One service per resource; CRUD logic",
    "tests/test_main.py": "pytest + httpx tests for CRUD + error cases",
    "requirements.txt": "Minimal dependencies needed to run and test"
  }}
}}

Output requirements (MANDATORY)
- Return ONLY valid JSON.
- The JSON MUST be exactly: {{"files": {{...}}}} with file paths as keys and full file contents as values.
- Do not include markdown fences, explanations, comments outside code, or extra top-level keys.

Quality checklist (MANDATORY)
1) All imports resolve; no missing symbols.
2) Endpoints match the endpoint spec (method/path/inputs/outputs).
3) CRUD is complete for each resource unless the spec says otherwise.
4) Tests are runnable and cover: create, list, get, update, delete, and not-found.
"""

    response = await llm.ainvoke([
        SystemMessage(content=CODE_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    # Parse response
    try:
        data = json.loads(response.content)
        files = data.get("files", {})
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(content[start:end])
                files = data.get("files", {})
            except json.JSONDecodeError:
                files = {}

    if not files:
        return {
            "error_message": "Failed to generate code files",
            "current_stage": WorkflowStage.FAILED,
        }
    #TODO :: nested folder
    # Validate generated code
    validation_errors = []
    for filename, content in files.items():
        if filename.endswith(".py"):
            # Syntax validation
            syntax_result = validate_python_syntax.invoke(content)
            if not syntax_result["valid"]:
                validation_errors.extend([
                    f"{filename}: {e['message']} (line {e['line']})"
                    for e in syntax_result["errors"]
                ])

            # FastAPI pattern check
            pattern_result = check_fastapi_patterns.invoke(content)
            validation_errors.extend([
                f"{filename}: {issue}"
                for issue in pattern_result.get("issues", [])
            ])

            # FastAPI-only check
            fastapi_only = validate_fastapi_only.invoke(content)
            if not fastapi_only["valid"]:
                validation_errors.extend([
                    f"{filename}: {issue}"
                    for issue in fastapi_only["issues"]
                ])

    # Generate requirements.txt if not present
    if "requirements.txt" not in files:
        all_code = "\n".join(files.values())
        imports = extract_imports.invoke(all_code)
        files["requirements.txt"] = generate_requirements.invoke(imports)

    # Create code artifact
    code_artifact = {
        "id": None,
        "spec_ids": [s.get("id") for s in approved_specs],
        "files": files,
        "validation_report": {
            "pre_validation_errors": validation_errors,
            "status": "pending_validation",
        },
        "lint_results": [],
        "test_results": [],
        "status": "draft",
        "fix_attempts": 0,
    }

    return {
        "code_artifacts": [code_artifact],
        "validation_errors": validation_errors,
        "current_stage": WorkflowStage.VALIDATION,
        "user_feedback": None,
    }


# @observe(name="fix_code")
async def fix_code_node(state: WorkflowState) -> dict[str, Any]:
    """
    Attempt to fix validation errors in generated code.
    """
    code_artifacts = state.get("code_artifacts", [])
    validation_errors = state.get("validation_errors", [])

    if not code_artifacts or not validation_errors:
        return {}

    artifact = code_artifacts[0]
    fix_attempts = artifact.get("fix_attempts", 0)
    max_attempts = state.get("max_retries", 3)

    if fix_attempts >= max_attempts:
        return {
            "error_message": f"Failed to fix code after {max_attempts} attempts",
            "current_stage": WorkflowStage.FAILED,
        }

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.1,
        api_key=settings.openai_api_key,
    )

    prompt = f"""Fix these validation errors in the generated FastAPI code:

Errors:
{json.dumps(validation_errors, indent=2)}

Current Files:
{json.dumps(artifact.get('files', {}), indent=2)}

Return a JSON object with "files" containing the fixed file contents.
Only include files that needed changes."""

    response = await llm.ainvoke([
        SystemMessage(content=CODE_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    try:
        data = json.loads(response.content)
        fixed_files = data.get("files", {})
    except json.JSONDecodeError:
        fixed_files = {}

    if fixed_files:
        # Merge fixed files
        artifact["files"].update(fixed_files)
        artifact["fix_attempts"] = fix_attempts + 1

        # Re-validate
        new_errors = []
        for filename, content in fixed_files.items():
            if filename.endswith(".py"):
                syntax_result = validate_python_syntax.invoke(content)
                if not syntax_result["valid"]:
                    new_errors.extend([
                        f"{filename}: {e['message']}"
                        for e in syntax_result["errors"]
                    ])

        return {
            "code_artifacts": [artifact],
            "validation_errors": new_errors,
            "current_stage": WorkflowStage.VALIDATION if new_errors else WorkflowStage.COMPLETED,
        }

    return {
        "code_artifacts": [artifact],
    }
