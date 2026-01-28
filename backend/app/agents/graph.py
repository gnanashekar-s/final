"""Main LangGraph workflow for product-to-code transformation."""
import asyncio
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.state import WorkflowStage, WorkflowState, create_initial_state, ApprovalStatus
from app.core.logging import WorkflowLogger, get_logger

logger = get_logger("graph")


# ============================================================================
# NODE WRAPPERS WITH LOGGING
# ============================================================================

async def research_node_wrapper(state: WorkflowState) -> dict[str, Any]:
    """Research node with logging."""
    from app.agents.nodes.research import research_node

    run_id = state.get("run_id", 0)
    wf_logger = WorkflowLogger(run_id)
    wf_logger.stage_start("RESEARCH")

    try:
        result = await research_node(state)

        artifact = result.get("research_artifact", {})
        url_count = len(artifact.get("urls", []))
        wf_logger.artifact_created("research URL", url_count)
        wf_logger.stage_end("RESEARCH", success=True)

        return result
    except Exception as e:
        wf_logger.error(f"Research failed: {e}", e)
        wf_logger.stage_end("RESEARCH", success=False)
        return {
            "current_stage": WorkflowStage.FAILED,
            "error_message": str(e),
        }


async def epic_generator_node_wrapper(state: WorkflowState) -> dict[str, Any]:
    """Epic generator node with logging."""
    from app.agents.nodes.epic_generator import epic_generator_node

    run_id = state.get("run_id", 0)
    wf_logger = WorkflowLogger(run_id)
    wf_logger.stage_start("EPIC GENERATION")

    try:
        result = await epic_generator_node(state)

        epics = result.get("epics", [])
        wf_logger.artifact_created("epic", len(epics))

        for i, epic in enumerate(epics):
            logger.info(f"    Epic {i+1}: {epic.get('title', 'Untitled')}")

        wf_logger.waiting_approval("epic", list(range(len(epics))))
        wf_logger.stage_end("EPIC GENERATION", success=True)

        return result
    except Exception as e:
        wf_logger.error(f"Epic generation failed: {e}", e)
        wf_logger.stage_end("EPIC GENERATION", success=False)
        return {
            "current_stage": WorkflowStage.FAILED,
            "error_message": str(e),
        }


async def story_generator_node_wrapper(state: WorkflowState) -> dict[str, Any]:
    """Story generator node with logging."""
    from app.agents.nodes.story_generator import story_generator_node

    run_id = state.get("run_id", 0)
    wf_logger = WorkflowLogger(run_id)
    wf_logger.stage_start("STORY GENERATION")

    try:
        result = await story_generator_node(state)

        stories = result.get("stories", [])
        wf_logger.artifact_created("story", len(stories))

        for i, story in enumerate(stories):
            logger.info(f"    Story {i+1}: {story.get('title', 'Untitled')}")

        wf_logger.waiting_approval("story", list(range(len(stories))))
        wf_logger.stage_end("STORY GENERATION", success=True)

        return result
    except Exception as e:
        wf_logger.error(f"Story generation failed: {e}", e)
        wf_logger.stage_end("STORY GENERATION", success=False)
        return {
            "current_stage": WorkflowStage.FAILED,
            "error_message": str(e),
        }


async def spec_generator_node_wrapper(state: WorkflowState) -> dict[str, Any]:
    """Spec generator node with logging."""
    from app.agents.nodes.spec_generator import spec_generator_node

    run_id = state.get("run_id", 0)
    wf_logger = WorkflowLogger(run_id)
    wf_logger.stage_start("SPEC GENERATION")

    try:
        result = await spec_generator_node(state)

        specs = result.get("specs", [])
        wf_logger.artifact_created("spec", len(specs))
        wf_logger.waiting_approval("spec", list(range(len(specs))))
        wf_logger.stage_end("SPEC GENERATION", success=True)

        return result
    except Exception as e:
        wf_logger.error(f"Spec generation failed: {e}", e)
        wf_logger.stage_end("SPEC GENERATION", success=False)
        return {
            "current_stage": WorkflowStage.FAILED,
            "error_message": str(e),
        }


async def code_generator_node_wrapper(state: WorkflowState) -> dict[str, Any]:
    """Code generator node with logging."""
    from app.agents.nodes.code_generator import code_generator_node

    run_id = state.get("run_id", 0)
    wf_logger = WorkflowLogger(run_id)
    wf_logger.stage_start("CODE GENERATION")

    try:
        result = await code_generator_node(state)

        artifacts = result.get("code_artifacts", [])
        if artifacts:
            files = artifacts[0].get("files", {})
            wf_logger.artifact_created("code file", len(files))
            for filename in files.keys():
                logger.info(f"    File: {filename}")

        wf_logger.stage_end("CODE GENERATION", success=True)
        return result
    except Exception as e:
        wf_logger.error(f"Code generation failed: {e}", e)
        wf_logger.stage_end("CODE GENERATION", success=False)
        return {
            "current_stage": WorkflowStage.FAILED,
            "error_message": str(e),
        }


async def validator_node_wrapper(state: WorkflowState) -> dict[str, Any]:
    """Validator node with logging."""
    from app.agents.nodes.validator import validator_node

    run_id = state.get("run_id", 0)
    wf_logger = WorkflowLogger(run_id)
    wf_logger.stage_start("VALIDATION")

    try:
        result = await validator_node(state)

        passed = result.get("validation_passed", False)
        errors = result.get("validation_errors", [])

        if passed:
            logger.info("    ✓ All validations passed!")
        else:
            logger.warning(f"    ✗ Validation failed with {len(errors)} errors")
            for error in errors[:5]:  # Show first 5 errors
                logger.warning(f"      - {error}")

        wf_logger.stage_end("VALIDATION", success=passed)
        return result
    except Exception as e:
        wf_logger.error(f"Validation failed: {e}", e)
        wf_logger.stage_end("VALIDATION", success=False)
        return {
            "current_stage": WorkflowStage.FAILED,
            "error_message": str(e),
        }


async def fix_code_node_wrapper(state: WorkflowState) -> dict[str, Any]:
    """Fix code node with logging."""
    from app.agents.nodes.code_generator import fix_code_node

    run_id = state.get("run_id", 0)
    wf_logger = WorkflowLogger(run_id)

    artifacts = state.get("code_artifacts", [])
    attempt = artifacts[0].get("fix_attempts", 0) + 1 if artifacts else 1

    wf_logger.stage_start(f"AUTO-FIX (Attempt {attempt})")

    try:
        result = await fix_code_node(state)
        wf_logger.stage_end(f"AUTO-FIX (Attempt {attempt})", success=True)
        return result
    except Exception as e:
        wf_logger.error(f"Auto-fix failed: {e}", e)
        wf_logger.stage_end(f"AUTO-FIX (Attempt {attempt})", success=False)
        return state


# ============================================================================
# REVIEW NODES (HITL Gates)
# ============================================================================

async def epic_review_node(state: WorkflowState) -> dict[str, Any]:
    """Human-in-the-loop gate for epic review."""
    run_id = state.get("run_id", 0)
    logger.info(f"[Run {run_id}] Epic review gate - awaiting_approval: {state.get('awaiting_approval')}")

    if not state.get("awaiting_approval"):
        # Process approval result
        from app.agents.nodes.epic_generator import process_epic_approval
        return await process_epic_approval(state)

    # Pause for user input
    logger.info(f"[Run {run_id}] Pausing for epic approval...")
    return {
        "awaiting_approval": True,
        "approval_type": "epic",
    }


async def story_review_node(state: WorkflowState) -> dict[str, Any]:
    """Human-in-the-loop gate for story review."""
    run_id = state.get("run_id", 0)
    logger.info(f"[Run {run_id}] Story review gate - awaiting_approval: {state.get('awaiting_approval')}")

    if not state.get("awaiting_approval"):
        from app.agents.nodes.story_generator import process_story_approval
        return await process_story_approval(state)

    logger.info(f"[Run {run_id}] Pausing for story approval...")
    return {
        "awaiting_approval": True,
        "approval_type": "story",
    }


async def spec_review_node(state: WorkflowState) -> dict[str, Any]:
    """Human-in-the-loop gate for spec review."""
    run_id = state.get("run_id", 0)
    logger.info(f"[Run {run_id}] Spec review gate - awaiting_approval: {state.get('awaiting_approval')}")

    if not state.get("awaiting_approval"):
        from app.agents.nodes.spec_generator import process_spec_approval
        return await process_spec_approval(state)

    logger.info(f"[Run {run_id}] Pausing for spec approval...")
    return {
        "awaiting_approval": True,
        "approval_type": "spec",
    }


# ============================================================================
# ROUTER FUNCTIONS
# ============================================================================

def research_router(state: WorkflowState) -> Literal["continue", "retry", "fail"]:
    """Route after research node."""
    artifact = state.get("research_artifact")

    if not artifact or not artifact.get("findings"):
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count < max_retries:
            logger.info(f"Research incomplete, retrying ({retry_count + 1}/{max_retries})")
            return "retry"
        logger.error("Research failed after max retries")
        return "fail"

    logger.info("Research complete, continuing to epic generation")
    return "continue"


def epic_review_router(state: WorkflowState) -> Literal["approved", "rejected", "pending"]:
    """Route after epic review."""
    if not state.get("awaiting_approval", True):
        current_stage = state.get("current_stage")
        if current_stage == WorkflowStage.STORY_GENERATION:
            logger.info("Epics approved, continuing to story generation")
            return "approved"
        elif current_stage == WorkflowStage.EPIC_GENERATION:
            logger.info("Epics rejected, regenerating")
            return "rejected"
    logger.info("Waiting for epic approval...")
    return "pending"


def story_review_router(state: WorkflowState) -> Literal["approved", "rejected", "pending"]:
    """Route after story review."""
    if not state.get("awaiting_approval", True):
        current_stage = state.get("current_stage")
        if current_stage == WorkflowStage.SPEC_GENERATION:
            logger.info("Stories approved, continuing to spec generation")
            return "approved"
        elif current_stage == WorkflowStage.STORY_GENERATION:
            logger.info("Stories rejected, regenerating")
            return "rejected"
    logger.info("Waiting for story approval...")
    return "pending"


def spec_review_router(state: WorkflowState) -> Literal["approved", "rejected", "pending"]:
    """Route after spec review."""
    if not state.get("awaiting_approval", True):
        current_stage = state.get("current_stage")
        if current_stage == WorkflowStage.CODE_GENERATION:
            logger.info("Specs approved, continuing to code generation")
            return "approved"
        elif current_stage == WorkflowStage.SPEC_GENERATION:
            logger.info("Specs rejected, regenerating")
            return "rejected"
    logger.info("Waiting for spec approval...")
    return "pending"


def validation_router(state: WorkflowState) -> Literal["complete", "retry", "fail"]:
    """Route after validation."""
    if state.get("validation_passed", False):
        logger.info("Validation passed! Workflow complete.")
        return "complete"

    code_artifacts = state.get("code_artifacts", [])
    if not code_artifacts:
        logger.error("No code artifacts to validate")
        return "fail"

    artifact = code_artifacts[0]
    fix_attempts = artifact.get("fix_attempts", 0)
    max_retries = state.get("max_retries", 3)

    if fix_attempts < max_retries:
        logger.info(f"Validation failed, attempting auto-fix ({fix_attempts + 1}/{max_retries})")
        return "retry"

    logger.error(f"Validation failed after {max_retries} fix attempts")
    return "fail"


# ============================================================================
# GRAPH CREATION
# ============================================================================

def create_workflow_graph() -> StateGraph:
    """Create the main workflow graph for product-to-code transformation."""
    logger.info("Creating workflow graph...")

    # Create the graph
    graph = StateGraph(WorkflowState)

    # Add nodes with wrappers for logging
    graph.add_node("research", research_node_wrapper)
    graph.add_node("epic_generation", epic_generator_node_wrapper)
    graph.add_node("epic_review", epic_review_node)
    graph.add_node("story_generation", story_generator_node_wrapper)
    graph.add_node("story_review", story_review_node)
    graph.add_node("spec_generation", spec_generator_node_wrapper)
    graph.add_node("spec_review", spec_review_node)
    graph.add_node("code_generation", code_generator_node_wrapper)
    graph.add_node("validation", validator_node_wrapper)
    graph.add_node("auto_fix", fix_code_node_wrapper)

    # Set entry point
    graph.set_entry_point("research")

    # Add edges
    graph.add_conditional_edges(
        "research",
        research_router,
        {"continue": "epic_generation", "retry": "research", "fail": END},
    )

    graph.add_edge("epic_generation", "epic_review")

    graph.add_conditional_edges(
        "epic_review",
        epic_review_router,
        {"approved": "story_generation", "rejected": "epic_generation", "pending": END},
    )

    graph.add_edge("story_generation", "story_review")

    graph.add_conditional_edges(
        "story_review",
        story_review_router,
        {"approved": "spec_generation", "rejected": "story_generation", "pending": END},
    )

    graph.add_edge("spec_generation", "spec_review")

    graph.add_conditional_edges(
        "spec_review",
        spec_review_router,
        {"approved": "code_generation", "rejected": "spec_generation", "pending": END},
    )

    graph.add_edge("code_generation", "validation")

    graph.add_conditional_edges(
        "validation",
        validation_router,
        {"complete": END, "retry": "auto_fix", "fail": END},
    )

    graph.add_edge("auto_fix", "validation")

    logger.info("Workflow graph created successfully")
    return graph


# ============================================================================
# WORKFLOW RUNNER
# ============================================================================

class WorkflowRunner:
    """Runner class for executing the workflow with state management."""

    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer or MemorySaver()
        self._workflow = None

    @property
    def workflow(self):
        """Lazy initialization of workflow."""
        if self._workflow is None:
            graph = create_workflow_graph()
            self._workflow = graph.compile(checkpointer=self.checkpointer)
        return self._workflow

    async def start_workflow(
        self,
        run_id: int,
        project_id: int,
        user_id: int,
        product_request: str,
        constraints: str | None = None,
    ) -> dict[str, Any]:
        """Start a new workflow run."""
        logger.info(f"\n{'='*70}")
        logger.info(f"STARTING WORKFLOW - Run ID: {run_id}")
        logger.info(f"{'='*70}")
        logger.info(f"Product Request: {product_request[:100]}...")

        initial_state = create_initial_state(
            run_id=run_id,
            project_id=project_id,
            user_id=user_id,
            product_request=product_request,
            constraints=constraints,
        )

        config = {"configurable": {"thread_id": str(run_id)}}

        try:
            # Run until first HITL gate or completion
            result = await self.workflow.ainvoke(initial_state, config)

            logger.info(f"\n{'='*70}")
            logger.info(f"WORKFLOW PAUSED/COMPLETED - Run ID: {run_id}")
            logger.info(f"Current Stage: {result.get('current_stage')}")
            logger.info(f"Awaiting Approval: {result.get('awaiting_approval')}")
            logger.info(f"{'='*70}\n")

            return result
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise

    async def resume_workflow(
        self,
        run_id: int,
        updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resume a paused workflow with optional state updates."""
        logger.info(f"\n{'='*70}")
        logger.info(f"RESUMING WORKFLOW - Run ID: {run_id}")
        logger.info(f"{'='*70}")

        config = {"configurable": {"thread_id": str(run_id)}}

        if updates:
            current_state = await self.workflow.aget_state(config)
            if current_state and current_state.values:
                updated_state = {**current_state.values, **updates}
                await self.workflow.aupdate_state(config, updated_state)
                logger.info(f"State updated with: {list(updates.keys())}")

        try:
            result = await self.workflow.ainvoke(None, config)

            logger.info(f"\n{'='*70}")
            logger.info(f"WORKFLOW PAUSED/COMPLETED - Run ID: {run_id}")
            logger.info(f"Current Stage: {result.get('current_stage')}")
            logger.info(f"{'='*70}\n")

            return result
        except Exception as e:
            logger.error(f"Resume failed: {e}")
            raise

    async def get_state(self, run_id: int) -> dict[str, Any]:
        """Get the current state of a workflow run."""
        config = {"configurable": {"thread_id": str(run_id)}}
        state = await self.workflow.aget_state(config)
        return dict(state.values) if state and state.values else {}

    async def approve_items(
        self,
        run_id: int,
        item_type: str,
        item_ids: list[int],
        approved: bool,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """Approve or reject items and resume workflow."""
        action = "Approving" if approved else "Rejecting"
        logger.info(f"{action} {item_type}s: {item_ids}")

        state = await self.get_state(run_id)

        # Get the items list
        plural_map = {"epic": "epics", "story": "stories", "spec": "specs"}
        items_key = plural_map[item_type]

        items = state.get(items_key, [])

        # Update item statuses

        # Update item statuses (item_ids are list indices)
        for i, item in enumerate(items):
            if i in item_ids:
                item["status"] = (
                    ApprovalStatus.APPROVED.value if approved else ApprovalStatus.REJECTED.value
                )
                if not approved and feedback:
                    item["feedback"] = feedback
                logger.info(f"  Updated {item_type} {i}: {item['status']}")


        # Determine next stage based on approval
        if approved:
            next_stages = {
                "epic": WorkflowStage.STORY_GENERATION,
                "story": WorkflowStage.SPEC_GENERATION,
                "spec": WorkflowStage.CODE_GENERATION,
            }
            next_stage = next_stages.get(item_type, state.get("current_stage"))
        else:
            regen_stages = {
                "epic": WorkflowStage.EPIC_GENERATION,
                "story": WorkflowStage.STORY_GENERATION,
                "spec": WorkflowStage.SPEC_GENERATION,
            }
            next_stage = regen_stages.get(item_type, state.get("current_stage"))

        # Resume with updated state
        return await self.resume_workflow(
            run_id,
            {
                items_key: items,
                "awaiting_approval": False,
                "current_stage": next_stage,
            },
        )


# Global workflow runner instance
workflow_runner = WorkflowRunner()


def get_compiled_workflow(checkpointer=None):
    """Get a compiled workflow instance."""
    graph = create_workflow_graph()
    return graph.compile(checkpointer=checkpointer or MemorySaver())
