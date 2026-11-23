"""Web server for the VST3 chat: FastAPI + a static ChatGPT-style page."""

import json
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel

import auth
import chats
import main

main.check_env()

# Conversations live in memory, so run a single worker (see Dockerfile).
app_graph = main.build_graph(InMemorySaver())
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

# A new conversation is only saved once the user sends a first message, so that opening
# or reloading the page does not fill the history with empty conversations.
# thread_id -> (user id, the opening question the assistant showed)
_pending: dict[str, tuple[int, str]] = {}

STATIC = Path(__file__).parent / "static"
SESSION_COOKIE = "session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE") == "1"  # set when served over HTTPS


@asynccontextmanager
async def lifespan(_app):
    auth.init_db()
    chats.init_schema()
    yield


app = FastAPI(title="VST3 Creator", lifespan=lifespan)


class Credentials(BaseModel):
    username: str
    password: str


# Failed sign-ins per (ip, username): 10 in 15 minutes locks that pair out for the rest of the window.
_failures: dict[tuple[str, str], list[float]] = {}
FAIL_LIMIT, FAIL_WINDOW = 10, 15 * 60


def _recent_failures(key: tuple[str, str]) -> list[float]:
    now = time.time()
    recent = [t for t in _failures.get(key, []) if now - t < FAIL_WINDOW]
    _failures[key] = recent
    return recent


def _start_session(response: Response, user: dict) -> dict:
    token = auth.create_session(user["id"])
    response.set_cookie(
        SESSION_COOKIE, token, max_age=auth.SESSION_DAYS * 86400,
        httponly=True, samesite="lax", secure=COOKIE_SECURE,
    )
    return {"username": user["username"]}


def current_user(request: Request) -> dict:
    user = auth.user_for_session(request.cookies.get(SESSION_COOKIE))
    if not user:
        raise HTTPException(401, "Not signed in")
    return user


@app.post("/api/signup")
def signup(body: Credentials, response: Response):
    try:
        user = auth.create_user(body.username, body.password)
    except auth.AuthError as e:
        raise HTTPException(400, str(e))
    return _start_session(response, user)


@app.post("/api/login")
def login(body: Credentials, request: Request, response: Response):
    key = (request.client.host if request.client else "", body.username.strip().lower())
    if len(_recent_failures(key)) >= FAIL_LIMIT:
        raise HTTPException(429, "Too many failed attempts. Try again later.")
    try:
        user = auth.check_login(body.username, body.password)
    except auth.AuthError as e:
        _failures.setdefault(key, []).append(time.time())
        raise HTTPException(401, str(e))
    _failures.pop(key, None)
    return _start_session(response, user)


@app.post("/api/logout")
def logout(request: Request, response: Response):
    auth.delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return {"username": user["username"]}


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
        "download_url": f"/api/download/{thread_id}" if values.get("plugin_zip") else "",
    }


@app.post("/api/chat")
def chat(body: ChatIn, user: dict = Depends(current_user)):
    """Streams newline-delimited JSON: {"status": ...} while nodes run, then {"final": ...}."""
    if body.message is None:  # a new conversation, owned by the signed-in user
        thread_id = uuid.uuid4().hex
        _pending[thread_id] = (user["id"], "")
    else:
        thread_id = body.thread_id or ""
        pending = _pending.get(thread_id)
        if not ((pending and pending[0] == user["id"]) or chats.owner(thread_id) == user["id"]):
            raise HTTPException(404, "Conversation not found")
    config = {"configurable": {"thread_id": thread_id}}
    if body.message is None:
        graph_input = {"messages": []}
    else:
        if not body.message.strip():
            raise HTTPException(400, "Empty message")
        if not app_graph.get_state(config).next:
            raise HTTPException(409, "Conversation not active or already finished")
        graph_input = Command(resume=body.message)
        if pending:  # first message: the conversation is saved from here on
            chats.create_conversation(thread_id, user["id"])
            if pending[1]:
                chats.add_message(thread_id, "assistant", pending[1])
            del _pending[thread_id]
        chats.add_message(thread_id, "user", body.message)
        chats.set_title_from(thread_id, body.message)

    def events():
        with _lock_for(thread_id):
            last = {}
            try:
                for mode, chunk in app_graph.stream(graph_input, config, stream_mode=["custom", "values"]):
                    if mode == "custom":
                        yield json.dumps(chunk) + "\n"
                    else:
                        last = chunk
                event = _final_event(thread_id, last)
                if thread_id in _pending:
                    _pending[thread_id] = (user["id"], event["reply"])
                else:
                    chats.add_message(thread_id, "assistant", event["reply"], bool(event.get("download_url")))
                    if event.get("download_url"):
                        chats.set_plugin(thread_id, last["plugin_zip"])
                yield json.dumps({"final": event}) + "\n"
            except Exception as e:  # surface failures to the page instead of cutting the stream
                yield json.dumps({"error": f"{type(e).__name__}: {e}"}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


@app.get("/api/download/{thread_id}")
def download(thread_id: str, user: dict = Depends(current_user)):
    """Serve the built plugin zip for a finished conversation."""
    plugin_zip = chats.plugin_path(thread_id, user["id"])
    if not plugin_zip or not Path(plugin_zip).is_file():
        raise HTTPException(404, "No plugin available for this conversation")
    return FileResponse(plugin_zip, media_type="application/zip", filename="vst3-plugin.zip")


@app.get("/api/conversations")
def conversations(user: dict = Depends(current_user)):
    return chats.list_conversations(user["id"])


@app.get("/api/conversations/{thread_id}")
def conversation(thread_id: str, user: dict = Depends(current_user)):
    conv = chats.get_conversation(thread_id, user["id"])
    if not conv:
        raise HTTPException(404, "Conversation not found")
    # Still resumable only while the graph state is in memory (it is lost on a restart).
    conv["active"] = bool(app_graph.get_state({"configurable": {"thread_id": thread_id}}).next)
    return conv


@app.get("/healthz")
def healthz():
    return {"ok": True}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
