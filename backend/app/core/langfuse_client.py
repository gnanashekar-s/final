"""Langfuse observability client for tracing LLM calls."""
import functools
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

from app.config import settings

# Langfuse client instance (lazy initialization)
_langfuse_client = None


def get_langfuse():
    """Get or create the Langfuse client instance."""
    global _langfuse_client

    if _langfuse_client is None and settings.langfuse_secret_key:
        try:
            from langfuse import Langfuse

            _langfuse_client = Langfuse(
                secret_key=settings.langfuse_secret_key,
                public_key=settings.langfuse_public_key,
                host=settings.langfuse_host,
            )
        except ImportError:
            print("Warning: langfuse package not installed")
        except Exception as e:
            print(f"Warning: Failed to initialize Langfuse: {e}")

    return _langfuse_client


def observe(
    name: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Callable:
    """Decorator to observe/trace a function call with Langfuse."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            langfuse = get_langfuse()
            trace_name = name or func.__name__

            if langfuse is None:
                return await func(*args, **kwargs)

            trace = langfuse.start_span(
                name=trace_name,
                metadata={
                    "run_id": run_id,
                    **(metadata or {}),
                },
            )

            try:
                result = await func(*args, **kwargs)
                trace.update(output=str(result)[:1000])  # Truncate for safety
                return result
            except Exception as e:
                trace.update(
                    level="ERROR",
                    status_message=str(e),
                )
                raise
            finally:
                langfuse.flush()

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            langfuse = get_langfuse()
            trace_name = name or func.__name__

            if langfuse is None:
                return func(*args, **kwargs)

            trace = langfuse.start_span(
                name=trace_name,
                metadata={
                    "run_id": run_id,
                    **(metadata or {}),
                },
            )

            try:
                result = func(*args, **kwargs)
                trace.update(output=str(result)[:1000])
                return result
            except Exception as e:
                trace.update(
                    level="ERROR",
                    status_message=str(e),
                )
                raise
            finally:
                langfuse.flush()

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


@contextmanager
def trace_span(
    name: str,
    parent_trace_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Generator:
    """Context manager for creating a trace span."""
    langfuse = get_langfuse()

    if langfuse is None:
        yield None
        return

    if parent_trace_id:
        span = langfuse.start_span(
            name=name,
            trace_context={"trace_id": parent_trace_id},
            metadata=metadata,
        )
    else:
        trace = langfuse.start_span(name=name, metadata=metadata)
        span = trace

    try:
        yield span
    except Exception as e:
        span.update(level="ERROR", status_message=str(e))
        raise
    finally:
        langfuse.flush()


def log_generation(
    name: str,
    model: str,
    prompt: str,
    completion: str,
    tokens_input: int,
    tokens_output: int,
    run_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Log an LLM generation to Langfuse."""
    langfuse = get_langfuse()

    if langfuse is None:
        return

    trace = langfuse.start_span(
        name=name,
        metadata={
            "run_id": run_id,
            **(metadata or {}),
        },
    )

    trace.start_generation(
        name=f"{name}_generation",
        model=model,
        input=prompt,
        output=completion,
        usage_details={
            "input": tokens_input,
            "output": tokens_output,
        },
    )

    langfuse.flush()


def flush_langfuse() -> None:
    """Flush any pending Langfuse events."""
    langfuse = get_langfuse()
    if langfuse:
        langfuse.flush()


def shutdown_langfuse() -> None:
    """Shutdown the Langfuse client."""
    global _langfuse_client
    if _langfuse_client:
        _langfuse_client.flush()
        _langfuse_client.shutdown()
        _langfuse_client = None
