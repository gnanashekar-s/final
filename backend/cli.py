#!/usr/bin/env python3
"""
Product-to-Code CLI - Complete workflow executor with authentication.

This CLI simulates the entire product-to-code workflow:
1. User authentication (register/login)
2. Project creation
3. Workflow execution with HITL approvals
4. Code generation and export

Usage:
    python cli.py                    # Interactive mode
    python cli.py --auto-approve     # Auto-approve all stages
    python cli.py --help             # Show help
"""
import argparse
import asyncio
import getpass
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


# ============================================================================
# COLORS AND FORMATTING
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text: str):
    """Print a header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}\n")


def print_section(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'-'*50}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'-'*50}{Colors.END}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def print_stage(stage: str, status: str = "running"):
    """Print stage indicator."""
    if status == "running":
        print(f"\n{Colors.YELLOW}▶ {stage}...{Colors.END}")
    elif status == "complete":
        print(f"{Colors.GREEN}✓ {stage} complete{Colors.END}")
    elif status == "failed":
        print(f"{Colors.RED}✗ {stage} failed{Colors.END}")
    elif status == "waiting":
        print(f"{Colors.CYAN}⏸ {stage} - waiting for approval{Colors.END}")


# ============================================================================
# ENVIRONMENT CHECK
# ============================================================================

def check_environment() -> bool:
    """Check required environment variables."""
    print_section("Environment Check")

    openai_key = os.getenv("OPENAI_API_KEY", "")

    if not openai_key or openai_key.startswith("sk-your"):
        print_error("OPENAI_API_KEY not set in .env file")
        print_info("Please set your OpenAI API key in backend/.env")
        return False

    print_success(f"OPENAI_API_KEY: ***...{openai_key[-4:]}")

    # Optional checks
    langfuse_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    if langfuse_key:
        print_success("LANGFUSE: Configured")
    else:
        print_warning("LANGFUSE: Not configured (optional)")

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if tavily_key:
        print_success("TAVILY: Configured (better web search)")
    else:
        print_warning("TAVILY: Not configured (using OpenAI fallback)")

    return True


# ============================================================================
# USER AUTHENTICATION (Simulated - no database required)
# ============================================================================

class CLIUser:
    """Simple user class for CLI."""

    def __init__(self, user_id: int, email: str):
        self.id = user_id
        self.email = email


def authenticate_user() -> CLIUser:
    """Authenticate user (simulated for CLI)."""
    print_section("User Authentication")

    print("Enter your credentials (for tracking purposes):\n")

    email = input(f"{Colors.CYAN}Email: {Colors.END}").strip()
    if not email:
        email = "cli-user@example.com"
        print_info(f"Using default email: {email}")

    # For CLI, we just simulate authentication
    # In production, this would validate against the database
    user = CLIUser(user_id=1, email=email)
    print_success(f"Authenticated as: {user.email}")

    return user


# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================

class CLIProject:
    """Simple project class for CLI."""

    def __init__(self, project_id: int, name: str, product_request: str, constraints: str = None):
        self.id = project_id
        self.name = name
        self.product_request = product_request
        self.constraints = constraints


def create_project() -> CLIProject:
    """Create a new project interactively."""
    print_section("Project Setup")

    # Project name
    name = input(f"{Colors.CYAN}Project name: {Colors.END}").strip()
    if not name:
        name = f"CLI-Project-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        print_info(f"Using default name: {name}")

    # Product request
    print(f"\n{Colors.CYAN}Describe the product you want to build:{Colors.END}")
    print(f"{Colors.YELLOW}(This will be used to generate epics, stories, specs, and code){Colors.END}")
    print(f"{Colors.YELLOW}Example: Build a REST API for managing TODO items with user authentication{Colors.END}\n")

    product_request = input("> ").strip()
    if not product_request:
        product_request = "Build a simple REST API for managing TODO items with CRUD operations"
        print_info(f"Using default: {product_request}")

    # Constraints
    print(f"\n{Colors.CYAN}Any constraints or requirements? (optional, press Enter to skip):{Colors.END}")
    print(f"{Colors.YELLOW}Example: Use PostgreSQL, must support pagination, include rate limiting{Colors.END}\n")

    constraints = input("> ").strip() or None

    project = CLIProject(
        project_id=1,
        name=name,
        product_request=product_request,
        constraints=constraints,
    )

    print_success(f"Project created: {project.name}")

    return project


# ============================================================================
# WORKFLOW EXECUTION
# ============================================================================

def display_items(items: list, item_type: str):
    """Display items for approval."""
    print(f"\n{Colors.BOLD}Generated {len(items)} {item_type}(s):{Colors.END}\n")

    for i, item in enumerate(items):
        print(f"{Colors.CYAN}[{i}]{Colors.END} {Colors.BOLD}{item.get('title', f'{item_type} {i}')}{Colors.END}")

        if item_type == "epic":
            print(f"    Goal: {item.get('goal', 'N/A')[:80]}...")
            print(f"    Priority: {item.get('priority', 'medium')}")
            deps = item.get('dependencies', [])
            if deps:
                print(f"    Dependencies: {deps}")

        elif item_type == "story":
            print(f"    Epic: {item.get('epic_title', 'N/A')}")
            print(f"    Description: {item.get('description', 'N/A')[:80]}...")
            print(f"    Points: {item.get('story_points', 'N/A')}")

        elif item_type == "spec":
            print(f"    Story: {item.get('story_title', 'N/A')}")
            content = item.get('content', 'N/A')[:100]
            print(f"    Preview: {content}...")

        print()


def prompt_for_approval(items: list, item_type: str, auto_approve: bool = False) -> tuple[list[int], bool, str]:
    """Prompt user for approval decision."""
    display_items(items, item_type)

    if auto_approve:
        print_info("Auto-approving all items...")
        return list(range(len(items))), True, ""

    print(f"{Colors.BOLD}Options:{Colors.END}")
    print(f"  {Colors.GREEN}a/all{Colors.END}     - Approve all")
    print(f"  {Colors.GREEN}0,1,2{Colors.END}     - Approve specific items by index")
    print(f"  {Colors.RED}r/reject{Colors.END}  - Reject all (with feedback)")
    print(f"  {Colors.CYAN}v N{Colors.END}       - View item N in detail")
    print(f"  {Colors.YELLOW}q/quit{Colors.END}    - Quit workflow")
    print()

    while True:
        choice = input(f"{Colors.BOLD}Your choice: {Colors.END}").strip().lower()

        if choice in ["a", "all"]:
            return list(range(len(items))), True, ""

        if choice in ["r", "reject"]:
            feedback = input(f"{Colors.YELLOW}Feedback for rejection: {Colors.END}").strip()
            return list(range(len(items))), False, feedback

        if choice in ["q", "quit"]:
            print_warning("Exiting workflow...")
            sys.exit(0)

        if choice.startswith("v "):
            try:
                idx = int(choice.split()[1])
                if 0 <= idx < len(items):
                    print(f"\n{Colors.BOLD}--- {item_type.upper()} {idx} DETAILS ---{Colors.END}")
                    print(json.dumps(items[idx], indent=2, default=str))
                    print(f"{Colors.BOLD}--- END DETAILS ---{Colors.END}\n")
                else:
                    print_error("Invalid index")
            except (ValueError, IndexError):
                print_error("Invalid format. Use: v 0")
            continue

        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            if all(0 <= i < len(items) for i in indices):
                return indices, True, ""
            print_error("Some indices are out of range")
        except ValueError:
            print_error("Invalid input")


def display_code_files(files: dict):
    """Display generated code files."""
    print(f"\n{Colors.BOLD}Generated {len(files)} files:{Colors.END}\n")

    for filename in sorted(files.keys()):
        content = files[filename]
        lines = len(content.split('\n'))
        size = len(content)
        print(f"  {Colors.CYAN}📄 {filename}{Colors.END} ({lines} lines, {size} bytes)")


def save_generated_code(files: dict, output_dir: str = "generated_code"):
    """Save generated code to disk."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for filename, content in files.items():
        file_path = output_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    print_success(f"Code saved to: {output_path.absolute()}")
    return output_path


async def run_workflow(project: CLIProject, user: CLIUser, auto_approve: bool = False):
    """Execute the complete workflow."""
    from app.agents.graph import WorkflowRunner
    from app.agents.state import WorkflowStage
    from app.core.logging import setup_logging

    # Setup logging
    setup_logging("INFO")

    runner = WorkflowRunner()
    run_id = 1

    print_header("WORKFLOW EXECUTION")
    print(f"Project: {project.name}")
    print(f"Request: {project.product_request[:60]}...")
    if project.constraints:
        print(f"Constraints: {project.constraints}")
    print()

    # ========== STAGE 1: Start Workflow (Research + Epic Generation) ==========
    print_stage("Starting workflow (Research → Epic Generation)")

    try:
        state = await runner.start_workflow(
            run_id=run_id,
            project_id=project.id,
            user_id=user.id,
            product_request=project.product_request,
            constraints=project.constraints,
        )
    except Exception as e:
        print_error(f"Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Display research results
    if state.get("research_artifact"):
        artifact = state["research_artifact"]
        print_success(f"Research complete: {len(artifact.get('urls', []))} sources found")
        findings = artifact.get("findings", {})
        if findings.get("key_technologies"):
            print_info(f"Technologies: {', '.join(findings['key_technologies'][:5])}")

    # ========== APPROVAL LOOP ==========
    iteration = 0
    max_iterations = 20  # Safety limit

    while state.get("awaiting_approval") and iteration < max_iterations:
        iteration += 1
        # Code Generated by Sidekick is for learning and experimentation purposes only.
        approval_type = state.get("approval_type")

        plural_map = {"epic": "epics", "story": "stories", "spec": "specs"}
        items_key = plural_map.get(approval_type, f"{approval_type}s")

        items = state.get(items_key, [])


        if not items:
            print_error(f"No {approval_type}s found for approval")
            break

        print_stage(f"{approval_type.upper()} REVIEW", "waiting")

        # Get approval decision
        item_ids, approved, feedback = prompt_for_approval(items, approval_type, auto_approve)

        if approved:
            print_success(f"Approved {len(item_ids)} {approval_type}(s)")
        else:
            print_warning(f"Rejected with feedback: {feedback}")

        # Resume workflow with approval
        print_stage(f"Processing {approval_type} approval")

        try:
            state = await runner.approve_items(
                run_id=run_id,
                item_type=approval_type,
                item_ids=item_ids,
                approved=approved,
                feedback=feedback,
            )
        except Exception as e:
            print_error(f"Approval processing failed: {e}")
            import traceback
            traceback.print_exc()
            return None

        # Show progress
        current_stage = state.get("current_stage")
        if isinstance(current_stage, WorkflowStage):
            print_info(f"Current stage: {current_stage.value}")

    # ========== COMPLETION ==========
    current_stage = state.get("current_stage")

    if current_stage == WorkflowStage.COMPLETED:
        print_header("WORKFLOW COMPLETED SUCCESSFULLY!")

        # Summary
        print(f"  Epics: {len(state.get('epics', []))}")
        print(f"  Stories: {len(state.get('stories', []))}")
        print(f"  Specs: {len(state.get('specs', []))}")

        # Code artifacts
        if state.get("code_artifacts"):
            artifact = state["code_artifacts"][0]
            files = artifact.get("files", {})

            display_code_files(files)

            # Validation status
            if state.get("validation_passed"):
                print_success("All validations passed!")
            elif state.get("validation_errors"):
                print_warning(f"Validation had {len(state['validation_errors'])} issues")

            # Save code
            print()
            save_choice = input(f"{Colors.CYAN}Save generated code to disk? (y/n): {Colors.END}").strip().lower()
            if save_choice == "y":
                output_dir = input(f"{Colors.CYAN}Output directory (default: generated_code): {Colors.END}").strip()
                if not output_dir:
                    output_dir = "generated_code"
                save_generated_code(files, output_dir)

        return state

    elif current_stage == WorkflowStage.FAILED:
        print_header("WORKFLOW FAILED")
        print_error(f"Error: {state.get('error_message', 'Unknown error')}")
        return None

    else:
        print_warning(f"Workflow ended in unexpected state: {current_stage}")
        return state


# ============================================================================
# QUICK RUN MODE
# ============================================================================

async def quick_run(product_request: str, constraints: str = None, auto_approve: bool = False, output_dir: str = "generated_code"):
    """Quick run mode with minimal interaction."""
    print_header("PRODUCT-TO-CODE CLI (Quick Mode)")

    if not check_environment():
        sys.exit(1)

    user = CLIUser(user_id=1, email="cli-user@example.com")
    project = CLIProject(
        project_id=1,
        name=f"Quick-{datetime.now().strftime('%H%M%S')}",
        product_request=product_request,
        constraints=constraints,
    )

    print_info(f"Product Request: {product_request}")
    if constraints:
        print_info(f"Constraints: {constraints}")
    print_info(f"Auto-approve: {auto_approve}")
    print()

    state = await run_workflow(project, user, auto_approve=auto_approve)

    if state and state.get("code_artifacts"):
        files = state["code_artifacts"][0].get("files", {})
        if files and auto_approve:
            save_generated_code(files, output_dir)

    return state


# ============================================================================
# INTERACTIVE MODE
# ============================================================================

async def interactive_mode():
    """Full interactive mode."""
    print_header("PRODUCT-TO-CODE CLI")
    print("Transform your product ideas into working FastAPI code!\n")

    # Environment check
    if not check_environment():
        sys.exit(1)

    # Authentication
    user = authenticate_user()

    # Project setup
    project = create_project()

    # Confirm before starting
    print_section("Ready to Start")
    print(f"  Project: {project.name}")
    print(f"  Request: {project.product_request}")
    if project.constraints:
        print(f"  Constraints: {project.constraints}")
    print()

    confirm = input(f"{Colors.CYAN}Start workflow? (y/n): {Colors.END}").strip().lower()
    if confirm != "y":
        print_warning("Workflow cancelled")
        sys.exit(0)

    # Run workflow
    await run_workflow(project, user, auto_approve=False)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Product-to-Code CLI - Transform product ideas into FastAPI code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                                    # Interactive mode
  python cli.py "Build a TODO API"                 # Quick mode with prompt
  python cli.py -a "Build a blog API"              # Auto-approve all stages
  python cli.py -c "Use Redis" "Build a cache"    # With constraints
  python cli.py -o ./output "Build an API"         # Custom output directory
        """
    )

    parser.add_argument(
        "product_request",
        nargs="?",
        help="Product request (skips interactive mode)",
    )

    parser.add_argument(
        "-a", "--auto-approve",
        action="store_true",
        help="Automatically approve all stages",
    )

    parser.add_argument(
        "-c", "--constraints",
        help="Additional constraints for the project",
    )

    parser.add_argument(
        "-o", "--output",
        default="generated_code",
        help="Output directory for generated code (default: generated_code)",
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Force interactive mode even with product_request",
    )

    args = parser.parse_args()

    try:
        if args.product_request and not args.interactive:
            # Quick mode
            asyncio.run(quick_run(
                product_request=args.product_request,
                constraints=args.constraints,
                auto_approve=args.auto_approve,
                output_dir=args.output,
            ))
        else:
            # Interactive mode
            asyncio.run(interactive_mode())

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Workflow interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
