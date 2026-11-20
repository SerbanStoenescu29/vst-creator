"""Web server for the VST3 chat: FastAPI + a static ChatGPT-style page."""

import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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


@app.post("/api/chat")
def chat(body: ChatIn):
    thread_id = body.thread_id or uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}
    with _lock_for(thread_id):
        if body.message is None:
            result = app_graph.invoke({"messages": []}, config)
        else:
            if not body.message.strip():
                raise HTTPException(400, "Empty message")
            if not app_graph.get_state(config).next:
                raise HTTPException(409, "Conversation not active or already finished")
            result = app_graph.invoke(Command(resume=body.message), config)

    interrupts = result.get("__interrupt__")
    if interrupts:
        return {"thread_id": thread_id, "reply": interrupts[0].value, "done": False}
    return {
        "thread_id": thread_id,
        "reply": f"Thank you! Your plugin will be delivered to {result.get('email', '')}.",
        "done": True,
        "description": result.get("description", ""),
        "email": result.get("email", ""),
    }


@app.get("/healthz")
def healthz():
    return {"ok": True}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
