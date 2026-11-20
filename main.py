"""Minimalist VST requirements chat built with LangGraph.

Flow:
    collect    -> the user describes what they want
    assistant  -> the model answers in JSON; a conditional edge reads "action":
                  reply    -> back to collect (clarify / ask again)
                  continue -> fetch_sample -> write_code -> save_files -> build_plugin -> END

Run it two ways:

    python main.py                       the terminal
    langgraph dev --allow-blocking       LangGraph Studio, in the browser
"""

# CORPORATE TLS: use the OS certificate store (see truststore). Must run before
# anything opens a connection. Harmless if truststore is not installed.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

import json
import os
import sys
import uuid
from pathlib import Path
from typing import TypedDict

import httpx
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import traceable

from github_build import trigger_build
from sample_code import fetch_sample_code

# Load .env at import time: LangGraph Studio imports this file and never calls main().
load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
REQUIRED_ENV_VARS = ["OPENAI_API_KEY"]

SYSTEM_PROMPT = """You are a VST3 plugin generator for Windows.

Answer only on VST3 plugin related questions.

Do not talk about code and do not suggest coding frameworks. Do not promise to deliver anything other than the plugin, do not promise to deliver a user manual or any auxiliary items.

The answer will be in a JSON format.

Clarify with the user that the instructions are correct and complete.

When the user does not confirm, your output should be:
{
"action": "reply",
"answer": <your answer to the user>
}

When the user confirms that everything is correct and complete, ask for an e-mail address where the product will be delivered. When you have the confirmation that everything is correct and the e-mail address, the answer in this case should be:
{
"action" : "continue",
"full_description": full detailed description of what the user wants,
"email": user's e-mail address
}
"""


WRITE_CODE_PROMPT = """You are a VST3 plugin generator for Windows.
Given the following sample files:
CMakeLists.txt:
{cmake_lists}

PluginEditor.h:
{plugin_editor_h}

PluginEditor.cpp:
{plugin_editor_cpp}

PluginProcessor.h:
{plugin_processor_h}

PluginProcessor.cpp:
{plugin_processor_cpp}

And the following description:

{description}

Generate a VST3 plugin with C++ and Juce.

Rules:
 - do not change the CMakeLists.txt file and do not generate a new one.
 - do not add new dependencies
 - make sure that all your JUCE API calls are compatible with Juce 8.0.8
- return the output in the following JSON format:
{
"plugin_editor_h" : <content of PluginEditor.h>,
"plugin_editor_cpp" : <content of PluginEditor.cpp>,
"plugin_processor_h": <content of PluginProcessor.h,
"plugin_processor_cpp": <content of PluginProcessor.cpp>
}
"""


class VSTInfo(TypedDict, total=False):
    description: str
    email: str
    messages: list  # chat history sent to the model
    action: str  # "reply" or "continue", from the model's JSON
    sample_code: dict  # {cmake_lists, plugin_editor_cpp, ...} fetched once confirmed
    generated_code: dict  # {plugin_editor_h, plugin_editor_cpp, plugin_processor_h, plugin_processor_cpp}
    output_dir: str  # project folder (CMakeLists.txt + Source/) the sources were saved to
    build_branch: str  # GitHub branch the project was pushed to for the build
    build_url: str  # GitHub Actions page for the build workflow
    answer: str  # what to show the user when action == "reply"


@traceable(
    run_type="llm",
    name="openai",
    metadata={"ls_provider": "openai", "ls_model_name": OPENAI_MODEL},
)
def _openai_llm(messages, temperature):
    url = os.getenv("OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions")
    api_key = os.environ["OPENAI_API_KEY"]
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": OPENAI_MODEL, "messages": messages, "temperature": temperature},
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    usage = data.get("usage") or {}
    return {
        "messages": [data["choices"][0]["message"]],
        "usage_metadata": {
            "input_tokens": int(usage.get("prompt_tokens", 0)),
            "output_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)),
        },
    }


def call_openai(messages, temperature=0.3):
    return _openai_llm(messages, temperature)["messages"][0]["content"]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def parse_reply(raw: str) -> dict:
    """Parse the model's JSON answer. Unparseable output is treated as a reply."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("action") in ("reply", "continue"):
            return data
    except json.JSONDecodeError:
        pass
    return {"action": "reply", "answer": raw.strip()}


def collect(state: VSTInfo) -> dict:
    """Show the model's last answer (or the opening question) and read the user's reply."""
    prompt = state.get("answer") or "What would you like me to do?"
    user_text = interrupt(prompt)
    messages = list(state.get("messages") or [])
    messages.append({"role": "user", "content": user_text})
    return {"messages": messages}


def assistant(state: VSTInfo) -> dict:
    """Ask the model; its JSON answer decides what happens next."""
    messages = state["messages"]
    raw = call_openai([{"role": "system", "content": SYSTEM_PROMPT}, *messages])
    data = parse_reply(raw)
    messages = [*messages, {"role": "assistant", "content": raw.strip()}]
    if data["action"] == "continue":
        return {
            "messages": messages,
            "action": "continue",
            "description": data.get("full_description", ""),
            "email": data.get("email", ""),
        }
    return {"messages": messages, "action": "reply", "answer": str(data.get("answer", ""))}


def fetch_sample(state: VSTInfo) -> dict:
    """Download the sample plugin sources and keep them in the state."""
    return {"sample_code": fetch_sample_code()}


def _parse_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return json.loads(text)


def write_code(state: VSTInfo) -> dict:
    """Ask the model to write the plugin sources from the samples and the description."""
    values = {**state["sample_code"], "description": state["description"]}
    prompt = WRITE_CODE_PROMPT
    for key, value in values.items():  # str.replace: the prompt contains literal braces
        prompt = prompt.replace("{" + key + "}", value)
    raw = call_openai(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Generate the plugin now."},
        ],
        temperature=0.2,
    )
    return {"generated_code": _parse_json_object(raw)}


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))

# generated_code key -> file name written under <run folder>/Source/ (CMakeLists.txt goes in the run folder)
OUTPUT_FILES = {
    "plugin_editor_h": "PluginEditor.h",
    "plugin_editor_cpp": "PluginEditor.cpp",
    "plugin_processor_h": "PluginProcessor.h",
    "plugin_processor_cpp": "PluginProcessor.cpp",
}


def save_files(state: VSTInfo) -> dict:
    """Write the project (CMakeLists.txt + the four generated sources) to a new folder per run."""
    project_dir = OUTPUT_DIR / uuid.uuid4().hex
    source_dir = project_dir / "Source"
    source_dir.mkdir(parents=True)
    (project_dir / "CMakeLists.txt").write_text(state["sample_code"]["cmake_lists"], encoding="utf-8")
    for key, filename in OUTPUT_FILES.items():
        (source_dir / filename).write_text(state["generated_code"][key], encoding="utf-8")
    return {"output_dir": str(project_dir)}


def build_plugin(state: VSTInfo) -> dict:
    """Push the project to a GitHub branch and trigger the Visual Studio build workflow."""
    branch = f"build/{Path(state['output_dir']).name}"
    url = trigger_build(state["output_dir"], branch)
    return {"build_branch": branch, "build_url": url}


def route_after_assistant(state: VSTInfo) -> str:
    return "continue" if state["action"] == "continue" else "reply"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_graph(checkpointer=None):
    builder = StateGraph(VSTInfo)
    builder.add_node("collect", collect)
    builder.add_node("assistant", assistant)
    builder.add_node("fetch_sample", fetch_sample)
    builder.add_node("write_code", write_code)
    builder.add_node("save_files", save_files)
    builder.add_node("build_plugin", build_plugin)
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "assistant")
    builder.add_conditional_edges(
        "assistant",
        route_after_assistant,
        {"reply": "collect", "continue": "fetch_sample"},
    )
    builder.add_edge("fetch_sample", "write_code")
    builder.add_edge("write_code", "save_files")
    builder.add_edge("save_files", "build_plugin")
    builder.add_edge("build_plugin", END)
    return builder.compile(checkpointer=checkpointer)


# LANGGRAPH STUDIO: langgraph.json points at "main.py:graph". Studio supplies its
# own checkpointer, so none is passed here.
graph = build_graph()


def check_env():
    missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
    if missing:
        print(f"Missing required .env values: {', '.join(missing)}")
        raise SystemExit(1)


def main():
    check_env()
    app = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "cli"}}

    result = app.invoke({"messages": []}, config)
    while result.get("__interrupt__"):
        print(f"\nAI: {result['__interrupt__'][0].value}")
        reply = input("You: ")
        result = app.invoke(Command(resume=reply), config)

    print(f"\nConfirmed description:\n{result['description']}")


if __name__ == "__main__":
    sys.exit(main() or 0)
