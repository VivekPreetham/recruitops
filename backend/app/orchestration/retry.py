from langgraph.types import RetryPolicy
from pydantic import ValidationError

def is_retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is not None:
        if status in (408, 409, 429) or status >= 500:
            return True

        return status == 400 and "Tool_use_failed" in str(exc)
    return isinstance(exc, (TimeoutError, ValidationError, ConnectionError))

LLM_RETRY = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    backoff_factor=2.0,
    retry_on=is_retryable,
)