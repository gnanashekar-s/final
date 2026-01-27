"""File operations tools for code generation."""
import os
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class FileContent(BaseModel):
    """File content model."""
    filename: str
    content: str
    language: str = "python"


@tool
def create_file_structure(
    base_path: str,
    structure: dict,
) -> dict:
    """
    Create a file structure from a dictionary specification.

    Args:
        base_path: The base directory path
        structure: Dictionary mapping file paths to contents

    Returns:
        Dictionary with created files and any errors
    """
    created_files = []
    errors = []

    for filepath, content in structure.items():
        full_path = os.path.join(base_path, filepath)
        try:
            # Create directories if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Write file
            with open(full_path, "w") as f:
                f.write(content)

            created_files.append(filepath)
        except Exception as e:
            errors.append({"file": filepath, "error": str(e)})

    return {
        "created": created_files,
        "errors": errors,
        "base_path": base_path,
    }


@tool
def validate_file_structure(files: dict) -> dict:
    """
    Validate a proposed file structure for a FastAPI project.

    Args:
        files: Dictionary mapping filenames to content

    Returns:
        Validation results with any issues found
    """
    issues = []
    validated_files = []

    required_files = ["main.py", "requirements.txt"]
    recommended_patterns = {
        "main.py": ["from fastapi import FastAPI", "app = FastAPI"],
        "models.py": ["from sqlalchemy", "Base"],
        "schemas.py": ["from pydantic", "BaseModel"],
    }

    # Check for required files
    for required in required_files:
        found = any(f.endswith(required) for f in files.keys())
        if not found:
            issues.append(f"Missing required file: {required}")

    # Validate file contents
    for filename, content in files.items():
        file_issues = []

        # Check file extension
        if not filename.endswith(".py") and not filename.endswith(".txt") and not filename.endswith(".toml"):
            if not filename.endswith(".env") and not filename.endswith(".md"):
                file_issues.append(f"Unusual file extension: {filename}")

        # Check for recommended patterns
        base_name = os.path.basename(filename)
        if base_name in recommended_patterns:
            patterns = recommended_patterns[base_name]
            for pattern in patterns:
                if pattern not in content:
                    file_issues.append(f"Missing expected pattern in {filename}: {pattern}")

        # Check for security issues
        security_patterns = [
            ("password", "hardcoded password"),
            ("secret", "hardcoded secret"),
            ("api_key", "hardcoded API key"),
        ]
        for pattern, issue in security_patterns:
            if f'{pattern} = "' in content.lower() or f"{pattern} = '" in content.lower():
                file_issues.append(f"Potential security issue in {filename}: {issue}")

        if file_issues:
            issues.extend(file_issues)
        else:
            validated_files.append(filename)

    return {
        "valid": len(issues) == 0,
        "validated_files": validated_files,
        "issues": issues,
    }


@tool
def generate_init_files(directories: list[str]) -> dict[str, str]:
    """
    Generate __init__.py files for Python package directories.

    Args:
        directories: List of directory paths that need __init__.py

    Returns:
        Dictionary mapping __init__.py paths to their content
    """
    init_files = {}

    for directory in directories:
        init_path = os.path.join(directory, "__init__.py")
        # Generate a simple docstring-only __init__.py
        module_name = os.path.basename(directory)
        content = f'"""{module_name.title()} module."""\n'
        init_files[init_path] = content

    return init_files


@tool
def merge_file_contents(
    original: dict[str, str],
    updates: dict[str, str],
) -> dict[str, str]:
    """
    Merge file updates with original files.

    Args:
        original: Original file contents
        updates: Updated file contents

    Returns:
        Merged file contents
    """
    merged = original.copy()
    merged.update(updates)
    return merged


# Export tools
file_ops_tools = [
    create_file_structure,
    validate_file_structure,
    generate_init_files,
    merge_file_contents,
]
