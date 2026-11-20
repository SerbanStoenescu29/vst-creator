"""Web server for the VST3 chat: FastAPI + a static ChatGPT-style page."""

import json
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel

import main

main.check_env()

# Conversations live in memory, so run a single worker (see Dockerfile).
app_graph = main.build_graph(InMemorySaver())
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="VST3 Creator")


class ChatIn(BaseModel):
    thread_id: str | None = None
    message: str | None = None  # None starts a new conversation


def _lock_for(thread_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(thread_id, threading.Lock())


def _final_event(thread_id: str, values: dict) -> dict:
    interrupts = values.get("__interrupt__")
    if interrupts:
        return {"thread_id": thread_id, "reply": interrupts[0].value, "done": False}
    return {
        "thread_id": thread_id,
        "reply": values.get("build_message") or "Done.",
        "done": True,
        "description": values.get("description", ""),
        "email": values.get("email", ""),
    }


@app.post("/api/chat")
def chat(body: ChatIn):
    """Streams newline-delimited JSON: {"status": ...} while nodes run, then {"final": ...}."""
    thread_id = body.thread_id or uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}
    if body.message is None:
        graph_input = {"messages": []}
    else:
        if not body.message.strip():
            raise HTTPException(400, "Empty message")
        if not app_graph.get_state(config).next:
            raise HTTPException(409, "Conversation not active or already finished")
        graph_input = Command(resume=body.message)

    def events():
        with _lock_for(thread_id):
            last = {}
            try:
                for mode, chunk in app_graph.stream(graph_input, config, stream_mode=["custom", "values"]):
                    if mode == "custom":
                        yield json.dumps(chunk) + "\n"
                    else:
                        last = chunk
                yield json.dumps({"final": _final_event(thread_id, last)}) + "\n"
            except Exception as e:  # surface failures to the page instead of cutting the stream
                yield json.dumps({"error": f"{type(e).__name__}: {e}"}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


@app.get("/healthz")
def healthz():
    return {"ok": True}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
