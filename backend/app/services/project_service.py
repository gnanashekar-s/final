"""Project service for managing projects and runs."""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.code_artifact import CodeArtifact
from app.models.epic import Epic
from app.models.project import Project, ProjectStatus, TraceabilityMatrix
from app.models.run import ResearchArtifact, Run, RunStatus, WorkflowStage
from app.models.spec import Spec
from app.models.story import Story
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    """Service for project operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(
        self,
        user_id: int,
        project_data: ProjectCreate,
    ) -> Project:
        """Create a new project."""
        project = Project(
            user_id=user_id,
            name=project_data.name,
            product_request=project_data.product_request,
            status=ProjectStatus.DRAFT,
        )
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def get_project(
        self,
        project_id: int,
        user_id: int,
    ) -> Optional[Project]:
        """Get a project by ID for a specific user."""
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.runs))
            .where(Project.id == project_id, Project.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_projects(
        self,
        user_id: int,
        status: Optional[ProjectStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Project], int]:
        """Get paginated projects for a user."""
        query = select(Project).where(Project.user_id == user_id)

        if status:
            query = query.where(Project.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        # Get paginated results
        query = query.order_by(Project.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    async def update_project(
        self,
        project: Project,
        project_data: ProjectUpdate,
    ) -> Project:
        """Update a project."""
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project: Project) -> None:
        """Delete a project and all related data."""
        await self.db.delete(project)

    async def create_run(self, project_id: int) -> Run:
        """Create a new workflow run for a project."""
        run = Run(
            project_id=project_id,
            status=RunStatus.PENDING,
            current_stage=WorkflowStage.RESEARCH,
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def get_run(
        self,
        run_id: int,
        project_id: int,
    ) -> Optional[Run]:
        """Get a run by ID."""
        result = await self.db.execute(
            select(Run).where(Run.id == run_id, Run.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def update_run_status(
        self,
        run: Run,
        status: RunStatus,
        stage: Optional[WorkflowStage] = None,
        error_message: Optional[str] = None,
    ) -> Run:
        """Update a run's status."""
        run.status = status
        if stage:
            run.current_stage = stage
        if error_message:
            run.error_message = error_message

        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def save_checkpoint(
        self,
        run: Run,
        checkpoint_data: dict,
    ) -> Run:
        """Save checkpoint data for a run."""
        run.checkpoint_data = checkpoint_data
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def get_project_artifacts(
        self,
        project_id: int,
    ) -> dict:
        """Get all artifacts for a project."""
        # Get epics
        epics_result = await self.db.execute(
            select(Epic).where(Epic.project_id == project_id)
        )
        epics = list(epics_result.scalars().all())

        # Get stories for these epics
        epic_ids = [e.id for e in epics]
        stories_result = await self.db.execute(
            select(Story).where(Story.epic_id.in_(epic_ids))
        )
        stories = list(stories_result.scalars().all())

        # Get specs for these stories
        story_ids = [s.id for s in stories]
        specs_result = await self.db.execute(
            select(Spec).where(Spec.story_id.in_(story_ids))
        )
        specs = list(specs_result.scalars().all())

        # Get code artifacts for these specs
        spec_ids = [s.id for s in specs]
        code_result = await self.db.execute(
            select(CodeArtifact).where(CodeArtifact.spec_id.in_(spec_ids))
        )
        code_artifacts = list(code_result.scalars().all())

        return {
            "epics": epics,
            "stories": stories,
            "specs": specs,
            "code_artifacts": code_artifacts,
        }

    async def build_traceability_matrix(
        self,
        project_id: int,
    ) -> TraceabilityMatrix:
        """Build and save a traceability matrix for a project."""
        artifacts = await self.get_project_artifacts(project_id)

        # Build mapping
        mapping = {
            "epics": {},
            "stories": {},
            "specs": {},
            "code_artifacts": {},
        }

        for epic in artifacts["epics"]:
            epic_stories = [s for s in artifacts["stories"] if s.epic_id == epic.id]
            mapping["epics"][epic.id] = {
                "title": epic.title,
                "story_ids": [s.id for s in epic_stories],
            }

        for story in artifacts["stories"]:
            story_specs = [s for s in artifacts["specs"] if s.story_id == story.id]
            mapping["stories"][story.id] = {
                "title": story.title,
                "epic_id": story.epic_id,
                "spec_ids": [s.id for s in story_specs],
            }

        for spec in artifacts["specs"]:
            spec_code = [c for c in artifacts["code_artifacts"] if c.spec_id == spec.id]
            mapping["specs"][spec.id] = {
                "story_id": spec.story_id,
                "code_artifact_ids": [c.id for c in spec_code],
            }

        for code in artifacts["code_artifacts"]:
            mapping["code_artifacts"][code.id] = {
                "spec_id": code.spec_id,
                "files": list(code.files.keys()),
                "status": code.status.value,
            }

        # Save or update matrix
        result = await self.db.execute(
            select(TraceabilityMatrix).where(
                TraceabilityMatrix.project_id == project_id
            )
        )
        matrix = result.scalar_one_or_none()

        if matrix:
            matrix.mapping = mapping
        else:
            matrix = TraceabilityMatrix(
                project_id=project_id,
                mapping=mapping,
            )
            self.db.add(matrix)

        await self.db.flush()
        await self.db.refresh(matrix)
        return matrix
