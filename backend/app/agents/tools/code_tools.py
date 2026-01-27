"""Code generation and validation tools."""
import ast
import subprocess
import tempfile
from typing import Optional

from langchain_core.tools import tool


@tool
def validate_python_syntax(code: str) -> dict:
    """
    Validate Python code syntax.

    Args:
        code: Python code to validate

    Returns:
        Validation result with any syntax errors
    """
    try:
        ast.parse(code)
        return {"valid": True, "errors": []}
    except SyntaxError as e:
        return {
            "valid": False,
            "errors": [
                {
                    "line": e.lineno,
                    "column": e.offset,
                    "message": str(e.msg),
                }
            ],
        }


@tool
def check_fastapi_patterns(code: str) -> dict:
    """
    Check if code follows FastAPI patterns and conventions.

    Args:
        code: Python code to check

    Returns:
        Check results with any pattern violations
    """
    issues = []
    suggestions = []

    # Check for FastAPI app initialization
    if "FastAPI(" not in code and "from fastapi import" in code:
        issues.append("FastAPI import found but no FastAPI app instance created")

    # Check for proper async patterns
    if "async def" not in code and "@app." in code:
        suggestions.append("Consider using async endpoints for better performance")

    # Check for dependency injection
    if "Depends(" not in code and "def " in code and "@app." in code:
        suggestions.append("Consider using FastAPI dependency injection (Depends)")

    # Check for response models
    if "response_model=" not in code and "@app." in code:
        suggestions.append("Consider adding response_model for better API documentation")

    # Check for proper error handling
    if "HTTPException" not in code and "@app." in code:
        suggestions.append("Consider using HTTPException for proper error responses")

    # Check for CORS if it looks like an API
    if "FastAPI(" in code and "CORSMiddleware" not in code:
        suggestions.append("Consider adding CORS middleware for frontend integration")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
    }


@tool
def lint_python_code(code: str) -> list[dict]:
    """
    Lint Python code using ruff (if available) or basic checks.

    Args:
        code: Python code to lint

    Returns:
        List of lint issues
    """
    issues = []

    # Try using ruff if available
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name

        result = subprocess.run(
            ["ruff", "check", temp_path, "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.stdout:
            import json

            lint_results = json.loads(result.stdout)
            for item in lint_results:
                issues.append({
                    "line": item.get("location", {}).get("row", 0),
                    "column": item.get("location", {}).get("column", 0),
                    "code": item.get("code", ""),
                    "message": item.get("message", ""),
                    "severity": "warning" if item.get("code", "").startswith("W") else "error",
                })

        import os

        os.unlink(temp_path)

    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Fallback to basic checks
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                issues.append({
                    "line": i,
                    "column": 120,
                    "code": "E501",
                    "message": f"Line too long ({len(line)} > 120)",
                    "severity": "warning",
                })

            # Check for trailing whitespace
            if line != line.rstrip():
                issues.append({
                    "line": i,
                    "column": len(line.rstrip()) + 1,
                    "code": "W291",
                    "message": "Trailing whitespace",
                    "severity": "warning",
                })

    return issues


@tool
def extract_imports(code: str) -> dict:
    """
    Extract all imports from Python code.

    Args:
        code: Python code to analyze

    Returns:
        Dictionary with standard, third-party, and local imports
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"error": "Invalid Python syntax"}

    standard_lib = []
    third_party = []
    local = []

    # Standard library modules (partial list)
    stdlib_modules = {
        "os", "sys", "json", "datetime", "typing", "pathlib", "re",
        "collections", "itertools", "functools", "asyncio", "logging",
        "io", "tempfile", "subprocess", "uuid", "hashlib", "base64",
        "dataclasses", "enum", "abc", "contextlib", "copy",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in stdlib_modules:
                    standard_lib.append(alias.name)
                elif module.startswith("app.") or module.startswith("."):
                    local.append(alias.name)
                else:
                    third_party.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            root_module = module.split(".")[0]
            if root_module in stdlib_modules:
                standard_lib.append(module)
            elif module.startswith("app.") or module.startswith(".") or node.level > 0:
                local.append(module)
            else:
                third_party.append(module)

    return {
        "standard_library": list(set(standard_lib)),
        "third_party": list(set(third_party)),
        "local": list(set(local)),
    }


@tool
def generate_requirements(imports: dict) -> str:
    """
    Generate requirements.txt content from extracted imports.

    Args:
        imports: Dictionary with third_party imports

    Returns:
        Requirements.txt content
    """
    # Map common imports to package names
    package_map = {
        "fastapi": "fastapi>=0.104.0",
        "pydantic": "pydantic>=2.0.0",
        "sqlalchemy": "sqlalchemy>=2.0.0",
        "uvicorn": "uvicorn[standard]>=0.24.0",
        "jose": "python-jose[cryptography]>=3.3.0",
        "passlib": "passlib[bcrypt]>=1.7.4",
        "langchain": "langchain>=0.1.0",
        "langchain_core": "langchain-core>=0.1.0",
        "langchain_openai": "langchain-openai>=0.0.5",
        "langgraph": "langgraph>=0.0.40",
        "openai": "openai>=1.0.0",
        "tavily": "tavily-python>=0.3.0",
        "langfuse": "langfuse>=2.0.0",
        "asyncpg": "asyncpg>=0.29.0",
        "alembic": "alembic>=1.13.0",
        "pydantic_settings": "pydantic-settings>=2.0.0",
        "pytest": "pytest>=7.4.0",
        "httpx": "httpx>=0.25.0",
    }

    requirements = []
    third_party = imports.get("third_party", [])

    for module in third_party:
        root_module = module.split(".")[0]
        if root_module in package_map:
            requirements.append(package_map[root_module])
        else:
            # Try to use the module name as package name
            requirements.append(root_module)

    # Remove duplicates and sort
    requirements = sorted(set(requirements))

    return "\n".join(requirements)


@tool
def validate_fastapi_only(code: str) -> dict:
    """
    Validate that code is FastAPI-only (no frontend frameworks).

    Args:
        code: Code to validate

    Returns:
        Validation result
    """
    forbidden_patterns = [
        ("react", "React/frontend code detected"),
        ("vue", "Vue/frontend code detected"),
        ("angular", "Angular/frontend code detected"),
        ("streamlit", "Streamlit code detected"),
        ("flask", "Flask code detected - use FastAPI instead"),
        ("django", "Django code detected - use FastAPI instead"),
        ("<html", "HTML template detected"),
        ("<div", "HTML/JSX detected"),
        ("document.", "Browser JavaScript detected"),
        ("window.", "Browser JavaScript detected"),
    ]

    issues = []
    code_lower = code.lower()

    for pattern, message in forbidden_patterns:
        if pattern in code_lower:
            issues.append(message)

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


# Export tools
code_tools = [
    validate_python_syntax,
    check_fastapi_patterns,
    lint_python_code,
    extract_imports,
    generate_requirements,
    validate_fastapi_only,
]
