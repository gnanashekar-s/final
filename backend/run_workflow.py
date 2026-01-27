#!/usr/bin/env python3
"""
CLI runner for testing the workflow without frontend.

Usage:
    python run_workflow.py "Build a TODO API with user authentication"
    python run_workflow.py --auto-approve "Build a simple REST API"
    python run_workflow.py --interactive "Build a blog API"
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.graph import WorkflowRunner
from app.agents.state import WorkflowStage
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging("DEBUG")
logger = get_logger("cli")


def print_banner():
    """Print CLI banner."""
    print("\n" + "=" * 70)
    print("  PRODUCT-TO-CODE WORKFLOW CLI RUNNER")
    print("=" * 70 + "\n")


def print_state_summary(state: dict):
    """Print a summary of the current state."""
    print("\n" + "-" * 50)
    print("CURRENT STATE SUMMARY")
    print("-" * 50)
    print(f"Stage: {state.get('current_stage')}")
    print(f"Awaiting Approval: {state.get('awaiting_approval')}")
    print(f"Approval Type: {state.get('approval_type')}")

    if state.get("research_artifact"):
        artifact = state["research_artifact"]
        print(f"\nResearch: {len(artifact.get('urls', []))} URLs found")

    if state.get("epics"):
        print(f"\nEpics ({len(state['epics'])}):")
        for i, epic in enumerate(state["epics"]):
            status = epic.get("status", "unknown")
            print(f"  [{i}] {status}: {epic.get('title', 'Untitled')}")

    if state.get("stories"):
        print(f"\nStories ({len(state['stories'])}):")
        for i, story in enumerate(state["stories"]):
            status = story.get("status", "unknown")
            print(f"  [{i}] {status}: {story.get('title', 'Untitled')}")

    if state.get("specs"):
        print(f"\nSpecs ({len(state['specs'])}):")
        for i, spec in enumerate(state["specs"]):
            status = spec.get("status", "unknown")
            print(f"  [{i}] {status}: Spec for story {spec.get('story_index', '?')}")

    if state.get("code_artifacts"):
        print(f"\nCode Artifacts ({len(state['code_artifacts'])}):")
        for artifact in state["code_artifacts"]:
            files = artifact.get("files", {})
            status = artifact.get("status", "unknown")
            print(f"  Status: {status}, Files: {len(files)}")
            for filename in list(files.keys())[:5]:
                print(f"    - {filename}")
            if len(files) > 5:
                print(f"    ... and {len(files) - 5} more files")

    if state.get("validation_errors"):
        print(f"\nValidation Errors ({len(state['validation_errors'])}):")
        for error in state["validation_errors"][:5]:
            print(f"  - {error}")

    print("-" * 50 + "\n")


def prompt_for_approval(approval_type: str, items: list) -> tuple[list[int], bool, str]:
    """Prompt user for approval decision."""
    print(f"\n{'='*50}")
    print(f"APPROVAL REQUIRED: {approval_type.upper()}S")
    print("=" * 50)

    for i, item in enumerate(items):
        print(f"\n[{i}] {item.get('title', f'{approval_type.title()} {i}')}")
        if approval_type == "epic":
            print(f"    Goal: {item.get('goal', 'N/A')[:100]}")
            print(f"    Scope: {item.get('scope', 'N/A')[:100]}")
        elif approval_type == "story":
            print(f"    Description: {item.get('description', 'N/A')[:100]}")
            print(f"    Points: {item.get('story_points', 'N/A')}")
        elif approval_type == "spec":
            content = item.get("content", "N/A")[:200]
            print(f"    Content: {content}...")

    print("\n" + "-" * 50)
    print("Options:")
    print("  a/all    - Approve all")
    print("  0,1,2    - Approve specific items by index")
    print("  r/reject - Reject all (with feedback)")
    print("  v/view N - View item N in detail")
    print("  q/quit   - Quit workflow")
    print("-" * 50)

    while True:
        choice = input("\nYour choice: ").strip().lower()

        if choice in ["a", "all"]:
            return list(range(len(items))), True, ""

        if choice in ["r", "reject"]:
            feedback = input("Feedback for rejection: ").strip()
            return list(range(len(items))), False, feedback

        if choice in ["q", "quit"]:
            print("Exiting workflow...")
            sys.exit(0)

        if choice.startswith("v ") or choice.startswith("view "):
            try:
                idx = int(choice.split()[1])
                if 0 <= idx < len(items):
                    print(f"\n--- {approval_type.upper()} {idx} DETAILS ---")
                    print(json.dumps(items[idx], indent=2, default=str))
                    print("--- END DETAILS ---\n")
            except (ValueError, IndexError):
                print("Invalid index")
            continue

        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            if all(0 <= i < len(items) for i in indices):
                return indices, True, ""
            print("Some indices are out of range")
        except ValueError:
            print("Invalid input. Use 'a' for all, numbers like '0,1,2', or 'r' to reject")


async def run_workflow_interactive(product_request: str, constraints: str = None):
    """Run workflow with interactive approvals."""
    runner = WorkflowRunner()
    run_id = 1  # Simple run ID for CLI

    logger.info(f"Starting workflow for: {product_request[:50]}...")

    # Start workflow
    state = await runner.start_workflow(
        run_id=run_id,
        project_id=1,
        user_id=1,
        product_request=product_request,
        constraints=constraints,
    )

    print_state_summary(state)

    # Loop until workflow completes or fails
    while state.get("awaiting_approval"):
        approval_type = state.get("approval_type")
        items_key = f"{approval_type}s"
        items = state.get(items_key, [])

        if not items:
            logger.error(f"No {approval_type}s found for approval")
            break

        # Get user decision
        item_ids, approved, feedback = prompt_for_approval(approval_type, items)

        # Apply approval
        state = await runner.approve_items(
            run_id=run_id,
            item_type=approval_type,
            item_ids=item_ids,
            approved=approved,
            feedback=feedback,
        )

        print_state_summary(state)

    # Final summary
    current_stage = state.get("current_stage")
    if current_stage == WorkflowStage.COMPLETED:
        print("\n" + "=" * 70)
        print("  WORKFLOW COMPLETED SUCCESSFULLY!")
        print("=" * 70)

        # Show generated code
        if state.get("code_artifacts"):
            artifact = state["code_artifacts"][0]
            files = artifact.get("files", {})
            print(f"\nGenerated {len(files)} files:")
            for filename in files.keys():
                print(f"  - {filename}")

            # Option to save files
            save = input("\nSave generated code to disk? (y/n): ").strip().lower()
            if save == "y":
                output_dir = Path("generated_code")
                output_dir.mkdir(exist_ok=True)
                for filename, content in files.items():
                    file_path = output_dir / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content)
                print(f"Code saved to: {output_dir.absolute()}")

    elif current_stage == WorkflowStage.FAILED:
        print("\n" + "=" * 70)
        print("  WORKFLOW FAILED")
        print("=" * 70)
        print(f"Error: {state.get('error_message', 'Unknown error')}")

    return state


async def run_workflow_auto_approve(product_request: str, constraints: str = None):
    """Run workflow with automatic approvals (for testing)."""
    runner = WorkflowRunner()
    run_id = 1

    logger.info(f"Starting workflow (auto-approve mode): {product_request[:50]}...")

    # Start workflow
    state = await runner.start_workflow(
        run_id=run_id,
        project_id=1,
        user_id=1,
        product_request=product_request,
        constraints=constraints,
    )

    print_state_summary(state)

    # Auto-approve everything
    while state.get("awaiting_approval"):
        approval_type = state.get("approval_type")
        items_key = f"{approval_type}s"
        items = state.get(items_key, [])

        if not items:
            break

        logger.info(f"Auto-approving {len(items)} {approval_type}(s)...")

        state = await runner.approve_items(
            run_id=run_id,
            item_type=approval_type,
            item_ids=list(range(len(items))),
            approved=True,
            feedback=None,
        )

        print_state_summary(state)

    return state


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="CLI runner for Product-to-Code workflow"
    )
    parser.add_argument(
        "product_request",
        nargs="?",
        default="Build a simple REST API for managing TODO items with CRUD operations",
        help="The product request to process",
    )
    parser.add_argument(
        "--constraints",
        "-c",
        help="Additional constraints for the workflow",
    )
    parser.add_argument(
        "--auto-approve",
        "-a",
        action="store_true",
        help="Automatically approve all items (for testing)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="generated_code",
        help="Output directory for generated code",
    )

    args = parser.parse_args()

    print_banner()
    print(f"Product Request: {args.product_request}")
    if args.constraints:
        print(f"Constraints: {args.constraints}")
    print(f"Mode: {'Auto-approve' if args.auto_approve else 'Interactive'}")
    print()

    try:
        if args.auto_approve:
            state = asyncio.run(
                run_workflow_auto_approve(args.product_request, args.constraints)
            )
        else:
            state = asyncio.run(
                run_workflow_interactive(args.product_request, args.constraints)
            )
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Workflow failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
