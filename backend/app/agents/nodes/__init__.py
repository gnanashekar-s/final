"""Agent nodes for the workflow graph."""
from app.agents.nodes.code_generator import code_generator_node, fix_code_node
from app.agents.nodes.epic_generator import (
    epic_generator_node,
    generate_epic_diagram,
    process_epic_approval,
)
from app.agents.nodes.research import research_node, should_continue_research
from app.agents.nodes.spec_generator import (
    generate_spec_diagrams,
    process_spec_approval,
    spec_generator_node,
)
from app.agents.nodes.story_generator import (
    estimate_stories,
    process_story_approval,
    story_generator_node,
)
from app.agents.nodes.validator import (
    run_tests,
    should_retry_validation,
    validator_node,
)

__all__ = [
    # Research
    "research_node",
    "should_continue_research",
    # Epic
    "epic_generator_node",
    "generate_epic_diagram",
    "process_epic_approval",
    # Story
    "story_generator_node",
    "estimate_stories",
    "process_story_approval",
    # Spec
    "spec_generator_node",
    "generate_spec_diagrams",
    "process_spec_approval",
    # Code
    "code_generator_node",
    "fix_code_node",
    # Validation
    "validator_node",
    "run_tests",
    "should_retry_validation",
]
