"""Calls to outside services that retry transient failures, and friendly messages for the ones that still fail."""

import logging
import time
import uuid

import httpx

log = logging.getLogger("vst")

RETRY_STATUS = {408, 429, 500, 502, 503, 504, 529}
ATTEMPTS = 3


def post(url: str, **kwargs) -> httpx.Response:
    """httpx.post that retries timeouts, connection errors, 429 and 5xx (twice, with a growing pause)."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = httpx.post(url, **kwargs)
        except (httpx.TransportError, httpx.TimeoutException):
            if attempt == ATTEMPTS:
                raise
            time.sleep(2 * attempt)
            continue
        if response.status_code in RETRY_STATUS and attempt < ATTEMPTS:
            try:
                pause = min(float(response.headers.get("retry-after", 2 * attempt)), 20)
            except ValueError:
                pause = 2 * attempt
            time.sleep(pause)
            continue
        response.raise_for_status()
        return response
    raise RuntimeError("unreachable")


def _service(exc: httpx.HTTPError) -> str:
    url = str(getattr(getattr(exc, "request", None), "url", "") or "")
    if "anthropic" in url:
        return "The code-writing AI"
    if "openai" in url:
        return "The AI service"
    if "github" in url:
        return "The build service"
    return "A required service"


def friendly_error(exc: BaseException) -> tuple[str, bool]:
    """(message for the user, whether trying again can help). The full error is logged with a short reference."""
    ref = uuid.uuid4().hex[:8]
    log.error("request failed [%s]: %r", ref, exc, exc_info=exc)
    retryable = True
    if isinstance(exc, httpx.HTTPStatusError):
        code, who = exc.response.status_code, _service(exc)
        if code in (401, 403):
            msg, retryable = f"{who} refused our credentials. This is a server configuration problem, not something you did.", False
        elif code == 429:
            msg = f"{who} is receiving too many requests right now. Please wait a minute and try again."
        elif code >= 500:
            msg = f"{who} is temporarily unavailable."
        else:
            msg, retryable = f"{who} could not process this request.", False
    elif isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        msg = "A required service did not answer in time."
    elif isinstance(exc, RuntimeError) and "GitHub" in str(exc):
        msg = "The build service (GitHub) had a problem."
    elif isinstance(exc, (ValueError, KeyError)):
        msg = "The AI returned an answer I could not use."
    else:
        msg = "Something went wrong."
    return f"{msg} (reference {ref})", retryable
