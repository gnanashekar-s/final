#!/usr/bin/env python3
"""
Simple test script to verify the workflow is functioning correctly.

This script tests the workflow step by step with detailed logging.
Run with: python test_workflow.py

Make sure you have:
1. Set OPENAI_API_KEY in your .env file
2. Optionally set LANGFUSE_* variables for observability
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Check required environment variables
def check_env():
    """Check required environment variables."""
    print("\n" + "=" * 60)
    print("ENVIRONMENT CHECK")
    print("=" * 60)

    openai_key = os.getenv("OPENAI_API_KEY", "")
    langfuse_secret = os.getenv("LANGFUSE_SECRET_KEY", "")
    langfuse_host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not openai_key or openai_key == "sk-your-openai-api-key":
        print("ERROR: OPENAI_API_KEY not set in .env file")
        print("Please set your OpenAI API key in backend/.env")
        return False

    print(f"OPENAI_API_KEY: {'*' * 20}...{openai_key[-4:]}")
    print(f"LANGFUSE_HOST: {langfuse_host}")
    print(f"LANGFUSE_SECRET_KEY: {'Set' if langfuse_secret else 'Not set (optional)'}")
    print("=" * 60 + "\n")
    return True


async def test_research_node():
    """Test the research node in isolation."""
    print("\n" + "=" * 60)
    print("TEST: Research Node")
    print("=" * 60)

    from app.agents.nodes.research import research_node
    from app.agents.state import create_initial_state

    # Create test state
    state = create_initial_state(
        run_id=1,
        project_id=1,
        user_id=1,
        product_request="Build a simple REST API for managing TODO items with CRUD operations",
        constraints="Use FastAPI and SQLAlchemy"
    )

    print(f"Product Request: {state['product_request']}")
    print(f"Constraints: {state['constraints']}")
    print("\nExecuting research node...")

    try:
        result = await research_node(state)

        print("\n--- Research Results ---")
        artifact = result.get("research_artifact", {})
        print(f"Queries: {result.get('research_queries', [])}")
        print(f"URLs found: {len(artifact.get('urls', []))}")

        findings = artifact.get("findings", {})
        print(f"\nFindings:")
        print(f"  Technologies: {findings.get('key_technologies', [])}")
        print(f"  Patterns: {findings.get('architecture_patterns', [])}")
        print(f"  Security: {findings.get('security_considerations', [])}")

        print("\nResearch node: SUCCESS")
        return result
    except Exception as e:
        print(f"\nResearch node FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_epic_node(research_result: dict):
    """Test the epic generator node."""
    print("\n" + "=" * 60)
    print("TEST: Epic Generator Node")
    print("=" * 60)

    from app.agents.nodes.epic_generator import epic_generator_node
    from app.agents.state import create_initial_state

    # Create state with research results
    state = create_initial_state(
        run_id=1,
        project_id=1,
        user_id=1,
        product_request="Build a simple REST API for managing TODO items with CRUD operations",
        constraints="Use FastAPI and SQLAlchemy"
    )

    # Add research results
    state["research_artifact"] = research_result.get("research_artifact", {})

    print("Executing epic generator node...")

    try:
        result = await epic_generator_node(state)

        print("\n--- Epic Results ---")
        epics = result.get("epics", [])
        print(f"Generated {len(epics)} epics:")

        for i, epic in enumerate(epics):
            print(f"\n  [{i}] {epic.get('title')}")
            print(f"      Goal: {epic.get('goal', '')[:60]}...")
            print(f"      Priority: {epic.get('priority')}")
            print(f"      Dependencies: {epic.get('dependencies', [])}")

        print(f"\nMermaid Diagram:\n{result.get('epic_dependency_graph', '')[:500]}...")

        print("\nEpic generator node: SUCCESS")
        return result
    except Exception as e:
        print(f"\nEpic generator node FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_full_workflow_start():
    """Test starting the full workflow."""
    print("\n" + "=" * 60)
    print("TEST: Full Workflow Start (with HITL pause)")
    print("=" * 60)

    from app.agents.graph import WorkflowRunner

    runner = WorkflowRunner()

    print("Starting workflow...")
    print("(Workflow will pause at epic review for approval)\n")

    try:
        state = await runner.start_workflow(
            run_id=99,
            project_id=1,
            user_id=1,
            product_request="Build a simple REST API for managing TODO items with CRUD operations",
            constraints="Use FastAPI and SQLAlchemy"
        )

        print("\n--- Workflow State After Start ---")
        print(f"Current Stage: {state.get('current_stage')}")
        print(f"Awaiting Approval: {state.get('awaiting_approval')}")
        print(f"Approval Type: {state.get('approval_type')}")

        if state.get("research_artifact"):
            artifact = state["research_artifact"]
            print(f"\nResearch: {len(artifact.get('urls', []))} URLs found")

        if state.get("epics"):
            print(f"\nEpics ({len(state['epics'])}):")
            for epic in state["epics"]:
                print(f"  - {epic.get('title')}")

        print("\nFull workflow start: SUCCESS")
        return runner, state
    except Exception as e:
        print(f"\nFull workflow start FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None, None


async def test_workflow_resume(runner, state):
    """Test resuming workflow after approval."""
    print("\n" + "=" * 60)
    print("TEST: Workflow Resume (Auto-approve epics)")
    print("=" * 60)

    if not runner or not state:
        print("Skipping - no runner/state from previous test")
        return None

    epics = state.get("epics", [])
    if not epics:
        print("Skipping - no epics to approve")
        return None

    print(f"Auto-approving {len(epics)} epics...")

    try:
        state = await runner.approve_items(
            run_id=99,
            item_type="epic",
            item_ids=list(range(len(epics))),
            approved=True,
            feedback=None
        )

        print("\n--- Workflow State After Resume ---")
        print(f"Current Stage: {state.get('current_stage')}")
        print(f"Awaiting Approval: {state.get('awaiting_approval')}")
        print(f"Approval Type: {state.get('approval_type')}")

        if state.get("stories"):
            print(f"\nStories ({len(state['stories'])}):")
            for story in state["stories"][:5]:  # Show first 5
                print(f"  - {story.get('title')}")
            if len(state["stories"]) > 5:
                print(f"  ... and {len(state['stories']) - 5} more")

        print("\nWorkflow resume: SUCCESS")
        return state
    except Exception as e:
        print(f"\nWorkflow resume FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  PRODUCT-TO-CODE WORKFLOW TEST SUITE")
    print("=" * 70)

    if not check_env():
        sys.exit(1)

    # Parse arguments
    test_mode = "all"
    if len(sys.argv) > 1:
        test_mode = sys.argv[1]

    print(f"Test mode: {test_mode}")
    print("(Options: all, research, epic, workflow)")

    if test_mode in ["all", "research"]:
        research_result = await test_research_node()
        if not research_result and test_mode != "all":
            sys.exit(1)
    else:
        research_result = None

    if test_mode in ["all", "epic"]:
        if research_result:
            await test_epic_node(research_result)
        else:
            print("\nSkipping epic test - need research results first")

    if test_mode in ["all", "workflow"]:
        runner, state = await test_full_workflow_start()
        if runner and state and state.get("awaiting_approval"):
            await test_workflow_resume(runner, state)

    print("\n" + "=" * 70)
    print("  TEST SUITE COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
