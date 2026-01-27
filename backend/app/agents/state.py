"""Shared state definition for the LangGraph workflow."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class WorkflowStage(str, Enum):
    """Workflow stage enum."""
    RESEARCH = "research"
    EPIC_GENERATION = "epic_generation"
    EPIC_REVIEW = "epic_review"
    STORY_GENERATION = "story_generation"
    STORY_REVIEW = "story_review"
    SPEC_GENERATION = "spec_generation"
    SPEC_REVIEW = "spec_review"
    CODE_GENERATION = "code_generation"
    VALIDATION = "validation"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    """Approval status for HITL gates."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ResearchArtifact:
    """Research artifact data."""
    urls: list[str] = field(default_factory=list)
    findings: dict[str, Any] = field(default_factory=dict)
    summary: str = ""


@dataclass
class EpicData:
    """Epic data structure."""
    id: Optional[int] = None
    title: str = ""
    goal: str = ""
    scope: str = ""
    priority: str = "medium"
    dependencies: list[int] = field(default_factory=list)
    mermaid_diagram: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    feedback: Optional[str] = None


@dataclass
class StoryData:
    """Story data structure."""
    id: Optional[int] = None
    epic_id: int = 0
    title: str = ""
    description: str = ""
    acceptance_criteria: list[dict] = field(default_factory=list)
    priority: str = "medium"
    story_points: Optional[int] = None
    edge_cases: list[str] = field(default_factory=list)
    status: ApprovalStatus = ApprovalStatus.PENDING
    feedback: Optional[str] = None


@dataclass
class SpecData:
    """Spec data structure."""
    id: Optional[int] = None
    story_id: int = 0
    content: str = ""
    requirements: dict[str, Any] = field(default_factory=dict)
    api_design: dict[str, Any] = field(default_factory=dict)
    data_model: dict[str, Any] = field(default_factory=dict)
    security_requirements: dict[str, Any] = field(default_factory=dict)
    test_plan: dict[str, Any] = field(default_factory=dict)
    mermaid_diagrams: dict[str, str] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    feedback: Optional[str] = None


@dataclass
class CodeArtifactData:
    """Code artifact data structure."""
    id: Optional[int] = None
    spec_id: int = 0
    files: dict[str, str] = field(default_factory=dict)
    validation_report: dict[str, Any] = field(default_factory=dict)
    lint_results: list[dict] = field(default_factory=list)
    test_results: list[dict] = field(default_factory=list)
    status: str = "draft"
    fix_attempts: int = 0


class WorkflowState(TypedDict, total=False):
    """Shared state for the LangGraph workflow."""

    # Run identification
    run_id: int
    project_id: int
    user_id: int

    # Input
    product_request: str
    constraints: Optional[str]

    # Current stage
    current_stage: WorkflowStage
    error_message: Optional[str]

    # Messages (for agent conversation)
    messages: Annotated[list, add_messages]

    # Research stage
    research_queries: list[str]
    research_artifact: Optional[dict]

    # Epic generation stage
    epics: list[dict]
    epic_dependency_graph: str  # Mermaid diagram

    # Story generation stage
    stories: list[dict]

    # Spec generation stage
    specs: list[dict]

    # Code generation stage
    code_artifacts: list[dict]

    # Validation stage
    validation_passed: bool
    validation_errors: list[str]

    # HITL gates
    awaiting_approval: bool
    approval_type: Optional[str]  # 'epic', 'story', 'spec'
    approval_ids: list[int]  # IDs of items awaiting approval
    user_feedback: Optional[str]

    # Retry tracking
    retry_count: int
    max_retries: int


def create_initial_state(
    run_id: int,
    project_id: int,
    user_id: int,
    product_request: str,
    constraints: Optional[str] = None,
) -> WorkflowState:
    """Create the initial workflow state."""
    return WorkflowState(
        run_id=run_id,
        project_id=project_id,
        user_id=user_id,
        product_request=product_request,
        constraints=constraints,
        current_stage=WorkflowStage.RESEARCH,
        error_message=None,
        messages=[],
        research_queries=[],
        research_artifact=None,
        epics=[],
        epic_dependency_graph="",
        stories=[],
        specs=[],
        code_artifacts=[],
        validation_passed=False,
        validation_errors=[],
        awaiting_approval=False,
        approval_type=None,
        approval_ids=[],
        user_feedback=None,
        retry_count=0,
        max_retries=3,
    )


def serialize_state(state: WorkflowState) -> dict:
    """Serialize state for checkpoint storage."""
    serialized = dict(state)
    # Convert enums to strings
    if "current_stage" in serialized and serialized["current_stage"]:
        serialized["current_stage"] = serialized["current_stage"].value
    return serialized


def deserialize_state(data: dict) -> WorkflowState:
    """Deserialize state from checkpoint storage."""
    if "current_stage" in data and isinstance(data["current_stage"], str):
        data["current_stage"] = WorkflowStage(data["current_stage"])
    return WorkflowState(**data)
