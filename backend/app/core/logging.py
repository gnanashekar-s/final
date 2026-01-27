"""Logging configuration for the application."""
import logging
import sys
from datetime import datetime
from typing import Optional

# Create custom formatter with colors
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        record.levelname = f"{color}{record.levelname}{reset}"
        record.name = f"\033[34m{record.name}{reset}"  # Blue for logger name
        return super().format(record)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Set up logging configuration."""
    # Create root logger
    logger = logging.getLogger("product_to_code")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(f"product_to_code.{name}")


# Agent-specific loggers
class WorkflowLogger:
    """Logger for workflow execution with structured output."""

    def __init__(self, run_id: int):
        self.run_id = run_id
        self.logger = get_logger(f"workflow.{run_id}")
        self.start_time = datetime.now()

    def stage_start(self, stage: str):
        """Log stage start."""
        self.logger.info(f"{'='*60}")
        self.logger.info(f"STAGE START: {stage}")
        self.logger.info(f"{'='*60}")

    def stage_end(self, stage: str, success: bool = True):
        """Log stage end."""
        status = "COMPLETED" if success else "FAILED"
        self.logger.info(f"STAGE {status}: {stage}")
        self.logger.info(f"{'='*60}")

    def agent_start(self, agent_name: str):
        """Log agent start."""
        self.logger.info(f"  → Starting agent: {agent_name}")

    def agent_end(self, agent_name: str, result_summary: str = ""):
        """Log agent end."""
        self.logger.info(f"  ← Agent {agent_name} completed: {result_summary}")

    def llm_call(self, model: str, prompt_preview: str):
        """Log LLM call."""
        preview = prompt_preview[:100] + "..." if len(prompt_preview) > 100 else prompt_preview
        self.logger.debug(f"    LLM call to {model}: {preview}")

    def llm_response(self, tokens: int, preview: str):
        """Log LLM response."""
        preview = preview[:100] + "..." if len(preview) > 100 else preview
        self.logger.debug(f"    LLM response ({tokens} tokens): {preview}")

    def tool_call(self, tool_name: str, args: dict):
        """Log tool call."""
        self.logger.debug(f"    Tool call: {tool_name}({args})")

    def tool_result(self, tool_name: str, result_preview: str):
        """Log tool result."""
        preview = result_preview[:100] + "..." if len(result_preview) > 100 else result_preview
        self.logger.debug(f"    Tool result: {tool_name} → {preview}")

    def artifact_created(self, artifact_type: str, count: int):
        """Log artifact creation."""
        self.logger.info(f"  ✓ Created {count} {artifact_type}(s)")

    def waiting_approval(self, artifact_type: str, ids: list):
        """Log waiting for approval."""
        self.logger.info(f"  ⏸ Waiting for approval: {artifact_type} IDs {ids}")

    def error(self, message: str, exc: Optional[Exception] = None):
        """Log error."""
        self.logger.error(f"  ✗ Error: {message}")
        if exc:
            self.logger.exception(exc)

    def progress(self, current: int, total: int, message: str):
        """Log progress."""
        percent = (current / total * 100) if total > 0 else 0
        self.logger.info(f"  [{percent:.0f}%] {message}")

    def elapsed_time(self) -> str:
        """Get elapsed time since start."""
        elapsed = datetime.now() - self.start_time
        return str(elapsed).split(".")[0]  # Remove microseconds


# Initialize default logging
setup_logging()
