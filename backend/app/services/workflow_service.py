"""Workflow service for managing workflow execution."""
import asyncio
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.agents import WorkflowRunner, serialize_state, workflow_runner
from app.config import settings
from app.core.logging import get_logger
from app.core.sse import sse_manager
from app.models.code_artifact import CodeArtifact, CodeArtifactStatus
from app.models.epic import Epic, EpicStatus
from app.models.project import Project, ProjectStatus
from app.models.run import ResearchArtifact, Run, RunStatus, WorkflowStage
from app.models.spec import Spec, SpecStatus
from app.models.story import Story, StoryStatus
from app.services.project_service import ProjectService

logger = get_logger("workflow_service")


class WorkflowService:
    """Service for workflow execution and management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_service = ProjectService(db)
        self.runner = workflow_runner
        

    async def start_workflow(
        self,
        project_id: int,
        user_id: int,
        launch_background: bool =True,
        constraints: Optional[str] = None,
    ) -> Run:
        """Start a new workflow run for a project.

        This method:
        1. Creates a new Run record in the database
        2. Updates the project status to IN_PROGRESS
        3. Starts the LangGraph workflow in a background task
        4. Returns the Run immediately (workflow continues asynchronously)
        """
        logger.info(f"Starting workflow for project {project_id} (user {user_id})")

        # Get project
        project = await self.project_service.get_project(project_id, user_id)
        if not project:
            raise ValueError("Project not found")

        logger.info(f"Project found: {project.name}")

        # Create run
        run = await self.project_service.create_run(project_id)
        logger.info(f"Created run {run.id}")

        # Update run status to running
        run = await self.project_service.update_run_status(
            run, RunStatus.RUNNING, WorkflowStage.RESEARCH
        )

        # Update project status
        project.status = ProjectStatus.IN_PROGRESS
        await self.db.flush()

        # Publish SSE event
        await sse_manager.publish_stage_update(
            run.id,
            "research",
            "Starting research phase...",
            0.0,
        )

        # Start workflow in background
        if launch_background:
            logger.info(f"Launching background task for run {run.id}")
            asyncio.create_task(
                self._execute_workflow(
                    run.id,
                    project_id,
                    user_id,
                    project.product_request,
                    constraints,
                )
            )

        return run
    async def execute_workflow_background(
        self,
        run_id: int,
        project_id: int,
        user_id: int,
        product_request: str,
        constraints,
    ) -> None:
        """Entry point for FastAPI BackgroundTasks."""
        await self._execute_workflow(
            run_id=run_id,
            project_id=project_id,
            user_id=user_id,
            product_request=product_request,
            constraints=constraints,
        )
    async def _execute_workflow(
        self,
        run_id: int,
        project_id: int,
        user_id: int,
        product_request: str,
        constraints: Optional[str],
    ) -> None:
        """Execute the workflow in background.

        Note: This runs in a background task, so we need to create
        a new database session for any database operations.
        """
        logger.info(f"Background workflow execution started for run {run_id}")

        try:
            result = await self.runner.start_workflow(
                run_id=run_id,
                project_id=project_id,
                user_id=user_id,
                product_request=product_request,
                constraints=constraints,
            )

            logger.info(f"Workflow returned for run {run_id}, processing result...")

            # Process result and save artifacts using a new session
            await self._process_workflow_result_with_new_session(run_id, result)

        except Exception as e:
            logger.error(f"Workflow execution failed for run {run_id}: {e}")

            # Update run status to failed using a new session
            try:
                from app.database import async_session_maker

                async with async_session_maker() as session:
                    run = await session.get(Run, run_id)
                    if run:
                        run.status = RunStatus.FAILED
                        run.error_message = str(e)
                        await session.commit()
                        logger.info(f"Updated run {run_id} status to FAILED")
            except Exception as db_error:
                logger.error(f"Failed to update run status: {db_error}")

            await sse_manager.publish_error(run_id, str(e), recoverable=False)

    async def _process_workflow_result_with_new_session(
        self,
        run_id: int,
        result: dict[str, Any],
    ) -> None:
        """Process workflow result with a new database session (for background tasks)."""
        from app.database import async_session_maker

        async with async_session_maker() as session:
            try:
                current_stage = result.get("current_stage")
                logger.info(f"Processing result for run {run_id}, stage: {current_stage}")

                # Handle different stages
                if result.get("awaiting_approval"):
                    await self._handle_approval_required_with_session(session, run_id, result)
                elif current_stage == WorkflowStage.COMPLETED:
                    await self._handle_completion_with_session(session, run_id, result)
                elif current_stage == WorkflowStage.FAILED:
                    await self._handle_failure_with_session(session, run_id, result)

                await session.commit()
            except Exception as e:
                logger.error(f"Error processing workflow result: {e}")
                await session.rollback()
                raise

    async def _handle_approval_required_with_session(
        self,
        session: AsyncSession,
        run_id: int,
        result: dict[str, Any],
    ) -> None:
        """Handle workflow paused for approval (with explicit session)."""
        approval_type = result.get("approval_type")
        approval_ids = result.get("approval_ids", [])

        run = await session.get(Run, run_id)
        if run:
            run.status = RunStatus.PAUSED
            run.checkpoint_data = serialize_state(result)
            logger.info(f"Run {run_id} paused for {approval_type} approval")

        await sse_manager.publish_approval_required(
            run_id,
            result.get("current_stage", "unknown").value if hasattr(result.get("current_stage"), "value") else str(result.get("current_stage")),
            approval_type,
            approval_ids,
            f"Awaiting approval for {len(approval_ids)} {approval_type}(s)",
        )

    async def _handle_completion_with_session(
        self,
        session: AsyncSession,
        run_id: int,
        result: dict[str, Any],
    ) -> None:
        """Handle workflow completion (with explicit session)."""
        run = await session.get(Run, run_id)
        if run:
            run.status = RunStatus.COMPLETED
            run.current_stage = WorkflowStage.COMPLETED
            logger.info(f"Run {run_id} completed successfully")

            project = await session.get(Project, run.project_id)
            if project:
                project.status = ProjectStatus.COMPLETED

        await sse_manager.publish_completion(
            run_id,
            success=True,
            message="Workflow completed successfully",
            artifacts={
                "epics_count": len(result.get("epics", [])),
                "stories_count": len(result.get("stories", [])),
                "specs_count": len(result.get("specs", [])),
                "code_artifacts_count": len(result.get("code_artifacts", [])),
            },
        )

    async def _handle_failure_with_session(
        self,
        session: AsyncSession,
        run_id: int,
        result: dict[str, Any],
    ) -> None:
        """Handle workflow failure (with explicit session)."""
        error_message = result.get("error_message", "Unknown error")

        run = await session.get(Run, run_id)
        if run:
            run.status = RunStatus.FAILED
            run.error_message = error_message
            logger.error(f"Run {run_id} failed: {error_message}")

            project = await session.get(Project, run.project_id)
            if project:
                project.status = ProjectStatus.FAILED

        await sse_manager.publish_error(run_id, error_message, recoverable=False)

    async def _process_workflow_result(
        self,
        run_id: int,
        result: dict[str, Any],
    ) -> None:
        """Process workflow result and update database (uses existing session)."""
        current_stage = result.get("current_stage")

        # Handle different stages
        if result.get("awaiting_approval"):
            await self._handle_approval_required(run_id, result)
        elif current_stage == WorkflowStage.COMPLETED:
            await self._handle_completion(run_id, result)
        elif current_stage == WorkflowStage.FAILED:
            await self._handle_failure(run_id, result)

    async def _handle_approval_required(
        self,
        run_id: int,
        result: dict[str, Any],
    ) -> None:
        """Handle workflow paused for approval."""
        approval_type = result.get("approval_type")
        approval_ids = result.get("approval_ids", [])

        # Update run status to paused
        run = await self.db.get(Run, run_id)
        if run:
            run.status = RunStatus.PAUSED
            run.checkpoint_data = serialize_state(result)
            await self.db.flush()

        # Publish SSE event
        await sse_manager.publish_approval_required(
            run_id,
            result.get("current_stage", "unknown").value,
            approval_type,
            approval_ids,
            f"Awaiting approval for {len(approval_ids)} {approval_type}(s)",
        )

    async def _handle_completion(
        self,
        run_id: int,
        result: dict[str, Any],
    ) -> None:
        """Handle workflow completion."""
        run = await self.db.get(Run, run_id)
        if run:
            run.status = RunStatus.COMPLETED
            run.current_stage = WorkflowStage.COMPLETED
            await self.db.flush()

            # Update project status
            project = await self.db.get(Project, run.project_id)
            if project:
                project.status = ProjectStatus.COMPLETED
                await self.db.flush()

        # Publish SSE event
        await sse_manager.publish_completion(
            run_id,
            success=True,
            message="Workflow completed successfully",
            artifacts={
                "epics_count": len(result.get("epics", [])),
                "stories_count": len(result.get("stories", [])),
                "specs_count": len(result.get("specs", [])),
                "code_artifacts_count": len(result.get("code_artifacts", [])),
            },
        )

    async def _handle_failure(
        self,
        run_id: int,
        result: dict[str, Any],
    ) -> None:
        """Handle workflow failure."""
        error_message = result.get("error_message", "Unknown error")

        run = await self.db.get(Run, run_id)
        if run:
            run.status = RunStatus.FAILED
            run.error_message = error_message
            await self.db.flush()

            # Update project status
            project = await self.db.get(Project, run.project_id)
            if project:
                project.status = ProjectStatus.FAILED
                await self.db.flush()

        await sse_manager.publish_error(run_id, error_message, recoverable=False)

    async def approve_artifacts(
        self,
        run_id: int,
        artifact_type: str,
        artifact_ids: list[int],
        approved: bool,
        feedback: Optional[str] = None,
    ) -> Run:
        """Approve or reject artifacts and resume workflow."""
        run = await self.db.get(Run, run_id)
        if not run:
            raise ValueError("Run not found")

        if run.status != RunStatus.PAUSED:
            raise ValueError("Run is not paused for approval")

        # Update run status
        run.status = RunStatus.RUNNING
        await self.db.flush()

        # Resume workflow with approval
        result = await self.runner.approve_items(
            run_id=run_id,
            item_type=artifact_type,
            item_ids=artifact_ids,
            approved=approved,
            feedback=feedback,
        )

        # Process result
        await self._process_workflow_result(run_id, result)

        return run

    async def get_workflow_state(self, run_id: int) -> dict[str, Any]:
        """Get the current workflow state."""
        return await self.runner.get_state(run_id)

    async def save_epics_to_db(
        self,
        run_id: int,
        project_id: int,
        epics_data: list[dict],
    ) -> list[Epic]:
        """Save generated epics to database."""
        epics = []
        for data in epics_data:
            epic = Epic(
                project_id=project_id,
                run_id=run_id,
                title=data.get("title", ""),
                goal=data.get("goal", ""),
                scope=data.get("scope", ""),
                priority=data.get("priority", "medium"),
                dependencies=data.get("dependencies"),
                mermaid_diagram=data.get("mermaid_diagram"),
                status=EpicStatus.PENDING_REVIEW,
            )
            self.db.add(epic)
            epics.append(epic)

        await self.db.flush()
        for epic in epics:
            await self.db.refresh(epic)

        return epics

    async def save_stories_to_db(
        self,
        epic_mapping: dict[int, int],  # index -> epic_id
        stories_data: list[dict],
    ) -> list[Story]:
        """Save generated stories to database."""
        stories = []
        for data in stories_data:
            epic_id = epic_mapping.get(data.get("epic_index", 0))
            if not epic_id:
                continue

            story = Story(
                epic_id=epic_id,
                title=data.get("title", ""),
                description=data.get("description", ""),
                acceptance_criteria=data.get("acceptance_criteria", []),
                priority=data.get("priority", "medium"),
                story_points=data.get("story_points"),
                edge_cases=data.get("edge_cases", []),
                status=StoryStatus.PENDING_REVIEW,
            )
            self.db.add(story)
            stories.append(story)

        await self.db.flush()
        for story in stories:
            await self.db.refresh(story)

        return stories

    async def save_specs_to_db(
        self,
        story_mapping: dict[int, int],  # index -> story_id
        specs_data: list[dict],
    ) -> list[Spec]:
        """Save generated specs to database."""
        specs = []
        for data in specs_data:
            story_id = story_mapping.get(data.get("story_index", 0))
            if not story_id:
                continue

            spec = Spec(
                story_id=story_id,
                content=data.get("content", ""),
                requirements=data.get("requirements"),
                api_design=data.get("api_design"),
                data_model=data.get("data_model"),
                security_requirements=data.get("security_requirements"),
                test_plan=data.get("test_plan"),
                mermaid_diagrams=data.get("mermaid_diagrams"),
                status=SpecStatus.PENDING_REVIEW,
            )
            self.db.add(spec)
            specs.append(spec)

        await self.db.flush()
        for spec in specs:
            await self.db.refresh(spec)

        return specs

    async def save_code_artifacts_to_db(
        self,
        spec_id: int,
        code_data: dict,
    ) -> CodeArtifact:
        """Save generated code artifact to database."""
        artifact = CodeArtifact(
            spec_id=spec_id,
            files=code_data.get("files", {}),
            validation_report=code_data.get("validation_report"),
            lint_results=code_data.get("lint_results"),
            test_results=code_data.get("test_results"),
            status=CodeArtifactStatus.DRAFT,
        )
        self.db.add(artifact)
        await self.db.flush()
        await self.db.refresh(artifact)
        return artifact
