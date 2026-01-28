"""Validator node for validating generated code."""
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.agents.state import WorkflowStage, WorkflowState
from app.agents.tools.code_tools import lint_python_code, validate_python_syntax
# from app.core.langfuse_client import observe


# @observe(name="validator_node")
async def validator_node(state: WorkflowState) -> dict[str, Any]:
    """
    Validate generated code through syntax, lint, and test checks.
    """
    code_artifacts = state.get("code_artifacts", [])

    if not code_artifacts:
        return {
            "error_message": "No code artifacts to validate",
            "current_stage": WorkflowStage.FAILED,
        }

    artifact = code_artifacts[0]
    files = artifact.get("files", {})

    validation_results = {
        "syntax_errors": [],
        "lint_errors": [],
        "test_results": [],
        "overall_passed": True,
    }

    # Syntax validation
    for filename, content in files.items():
        if filename.endswith(".py"):
            result = validate_python_syntax.invoke(content)
            if not result["valid"]:
                validation_results["syntax_errors"].extend([
                    {"file": filename, **error}
                    for error in result["errors"]
                ])
                validation_results["overall_passed"] = False

    # Lint validation
    for filename, content in files.items():
        if filename.endswith(".py"):
            lint_issues = lint_python_code.invoke(content)
            # Filter to errors only (not warnings)
            errors = [i for i in lint_issues if i.get("severity") == "error"]
            if errors:
                validation_results["lint_errors"].extend([
                    {"file": filename, **error}
                    for error in errors
                ])

    # Run tests if available
    test_files = {k: v for k, v in files.items() if "test" in k.lower()}
    if test_files:
        test_results = await run_tests(files)
        validation_results["test_results"] = test_results
        if any(not t.get("passed", False) for t in test_results):
            validation_results["overall_passed"] = False

    # Update artifact with validation results
    artifact["validation_report"] = validation_results
    artifact["lint_results"] = validation_results["lint_errors"]
    artifact["test_results"] = validation_results["test_results"]

    if validation_results["overall_passed"]:
        artifact["status"] = "valid"
        return {
            "code_artifacts": [artifact],
            "validation_passed": True,
            "validation_errors": [],
            "current_stage": WorkflowStage.COMPLETED,
        }
    else:
        # Collect all errors for potential auto-fix
        all_errors = []
        all_errors.extend([
            f"Syntax: {e['file']}:{e.get('line', 0)} - {e.get('message', '')}"
            for e in validation_results["syntax_errors"]
        ])
        all_errors.extend([
            f"Lint: {e['file']}:{e.get('line', 0)} - {e.get('message', '')}"
            for e in validation_results["lint_errors"]
        ])
        all_errors.extend([
            f"Test: {t.get('test_name', 'unknown')} - {t.get('error_message', 'failed')}"
            for t in validation_results["test_results"]
            if not t.get("passed", False)
        ])

        artifact["status"] = "invalid"

        return {
            "code_artifacts": [artifact],
            "validation_passed": False,
            "validation_errors": all_errors,
            "current_stage": WorkflowStage.VALIDATION,  # Will trigger fix loop
        }


async def run_tests(files: dict[str, str]) -> list[dict]:
    """
    Run tests in an isolated environment.
    """
    test_results = []

    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write all files
            for filename, content in files.items():
                filepath = tmppath / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)

            # Create a minimal test runner script
            runner_script = """
import sys
import json

results = []
try:
    import pytest
    exit_code = pytest.main(['-v', '--tb=short', '-q', str(sys.argv[1])])
    results.append({
        'test_name': 'pytest_suite',
        'passed': exit_code == 0,
        'error_message': None if exit_code == 0 else f'Exit code: {exit_code}'
    })
except ImportError:
    # pytest not available, try basic import test
    import importlib.util
    for py_file in sys.argv[2:]:
        try:
            spec = importlib.util.spec_from_file_location('module', py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            results.append({
                'test_name': f'import_{py_file}',
                'passed': True,
                'error_message': None
            })
        except Exception as e:
            results.append({
                'test_name': f'import_{py_file}',
                'passed': False,
                'error_message': str(e)
            })

print(json.dumps(results))
"""

            runner_path = tmppath / "_test_runner.py"
            runner_path.write_text(runner_script)

            # Get Python files for import testing
            py_files = [str(tmppath / f) for f in files if f.endswith(".py") and "test" not in f.lower()]

            # Run the test runner
            result = subprocess.run(
                ["python", str(runner_path), str(tmppath)] + py_files,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(tmppath),
            )

            if result.stdout:
                try:
                    test_results = json.loads(result.stdout.strip().split("\n")[-1])
                except json.JSONDecodeError:
                    test_results = [{
                        "test_name": "test_execution",
                        "passed": result.returncode == 0,
                        "error_message": result.stderr if result.returncode != 0 else None,
                    }]

    except subprocess.TimeoutExpired:
        test_results = [{
            "test_name": "test_execution",
            "passed": False,
            "error_message": "Test execution timed out",
        }]
    except Exception as e:
        test_results = [{
            "test_name": "test_execution",
            "passed": False,
            "error_message": str(e),
        }]

    return test_results


def should_retry_validation(state: WorkflowState) -> str:
    """
    Determine if validation should be retried with fixes.
    """
    if state.get("validation_passed", False):
        return "complete"

    code_artifacts = state.get("code_artifacts", [])
    if not code_artifacts:
        return "fail"

    artifact = code_artifacts[0]
    fix_attempts = artifact.get("fix_attempts", 0)
    max_retries = state.get("max_retries", 3)

    if fix_attempts < max_retries:
        return "retry"

    return "fail"


import json
