"""Agent tools."""
from app.agents.tools.code_tools import (
    check_fastapi_patterns,
    code_tools,
    extract_imports,
    generate_requirements,
    lint_python_code,
    validate_fastapi_only,
    validate_python_syntax,
)
from app.agents.tools.file_ops import (
    create_file_structure,
    file_ops_tools,
    generate_init_files,
    merge_file_contents,
    validate_file_structure,
)
from app.agents.tools.web_search import (
    search_best_practices,
    search_technical_docs,
    web_search,
    web_search_tools,
)

# All available tools
all_tools = web_search_tools + file_ops_tools + code_tools

__all__ = [
    # Web search tools
    "web_search",
    "search_technical_docs",
    "search_best_practices",
    "web_search_tools",
    # File ops tools
    "create_file_structure",
    "validate_file_structure",
    "generate_init_files",
    "merge_file_contents",
    "file_ops_tools",
    # Code tools
    "validate_python_syntax",
    "check_fastapi_patterns",
    "lint_python_code",
    "extract_imports",
    "generate_requirements",
    "validate_fastapi_only",
    "code_tools",
    # All tools
    "all_tools",
]
