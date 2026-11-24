"""Minimalist VST requirements chat built with LangGraph.

Flow:
    collect    -> the user describes what they want
    assistant  -> the model answers in JSON; a conditional edge reads "action":
                  reply    -> back to collect (clarify / ask again)
                  continue -> ask_ui: "do you have a picture of the UI?" (the model decides yes/no)
                      no  -> fetch_sample
                      yes -> ask_image (a picture is required) -> analyze_ui -> fetch_sample
                  fetch_sample -> retrieve_docs (RAG over the JUCE docs) -> write_code -> save_files -> build_plugin -> wait_for_build -> END (success)
                  wait_for_build failed -> retrieve_docs -> write_code again, with the build errors

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
import re
import sys
import uuid
from pathlib import Path
from typing import TypedDict

import httpx
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.config import get_stream_writer
from langgraph.types import Command, interrupt
from langsmith import traceable

from github_build import download_plugin, trigger_build, wait_for_build as poll_build
import agent
import spec as spec_mod
import rag
from sample_code import fetch_sample_code

# Load .env at import time: LangGraph Studio imports this file and never calls main().
load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
REQUIRED_ENV_VARS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]

SYSTEM_PROMPT = """You are a VST3 plugin generator for Windows.

Answer only on VST3 plugin related questions.

Do not talk about code and do not suggest coding frameworks. Do not promise to deliver anything other than the plugin, do not promise to deliver a user manual or any auxiliary items.

The answer will be in a JSON format.

Clarify with the user that the instructions are correct and complete.

You may ask if the user has UI design preferences, but do not ask for pictures yet.

When the user does not confirm, your output should be:
{
"action": "reply",
"answer": <your answer to the user>,
"spec": <the specification below, as far as you can draft it, or omit it if there is nothing to draft yet>
}

When the user confirms that everything is correct and complete, the answer in this case should be:
{
"action" : "continue",
"full_description": full detailed description of what the user wants,
"spec": <the specification below, complete>
}

The specification is a JSON object:
{
"name": short plugin name,
"type": "effect" or "instrument" or "midi_effect",
"summary": one sentence,
"parameters": [{"name": ..., "min": number, "max": number, "default": number, "unit": "Hz" or "dB" or "%" or "" ...}],
"ui_elements": [e.g. "rotary knob for each parameter", "level meter"],
"presets": [names, may be empty],
"missing": [things the user did not specify and you could not reasonably choose],
"assumptions": [values or choices you decided yourself because the user did not say]
}
Every plugin needs at least one parameter. Never invent facts silently: list them under "assumptions".
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

{rag_context}{previous_attempt}Generate a VST3 plugin with C++ and Juce.

Rules:
 - do not change the CMakeLists.txt file and do not generate a new one.
 - do not add new dependencies
 - make sure that all your JUCE API calls are compatible with Juce 8.0.8
- you are an agent with tools: use search_juce_docs whenever you are unsure about a JUCE class, method or signature,
  use validate_code on your files, fix any problems it reports, and finish by calling submit_plugin with the
  complete content of all four files. Do not print the files as text.
"""



class VSTInfo(TypedDict, total=False):
    description: str
    messages: list  # chat history sent to the model
    action: str  # "reply" or "continue", from the model's JSON
    spec: dict  # the structured plugin specification (spec.py)
    agent_trace: list  # tool calls the code agent made: [{"tool", "input", "result"}]
    rag_context: str  # JUCE documentation found by retrieve_docs
    sample_code: dict  # {cmake_lists, plugin_editor_cpp, ...} fetched once confirmed
    generated_code: dict  # {plugin_editor_h, plugin_editor_cpp, plugin_processor_h, plugin_processor_cpp}
    output_dir: str  # project folder (CMakeLists.txt + Source/) the sources were saved to
    build_branch: str  # GitHub branch the project was pushed to for the build
    build_url: str  # GitHub Actions page for the build workflow
    build_status: str  # "success", "failed" or "timeout"
    build_error: str  # compiler/CMake errors from the last failed build
    build_attempts: int  # how many builds have been started
    build_message: str  # final message shown to the user
    plugin_zip: str  # the built VST3 (zip) downloaded from the GitHub Actions artifact
    ui_choice: str  # "yes" / "no": does the user have a picture of the UI design
    ui_image: str  # the picture as a data URL, until it has been analysed
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


def _unwrap(value) -> tuple[str, str]:
    """A resume value is plain text (terminal) or {"text", "image"} (web page, image as a data URL)."""
    if isinstance(value, dict):
        return str(value.get("text") or ""), str(value.get("image") or "")
    return str(value or ""), ""


def collect(state: VSTInfo) -> dict:
    """Show the model's last answer (or the opening question) and read the user's reply."""
    prompt = state.get("answer") or "What would you like me to do?"
    user_text, _ = _unwrap(interrupt(prompt))
    messages = list(state.get("messages") or [])
    messages.append({"role": "user", "content": user_text})
    return {"messages": messages}


def assistant(state: VSTInfo) -> dict:
    """Ask the model; its JSON answer decides what happens next."""
    messages = state["messages"]
    raw = call_openai([{"role": "system", "content": SYSTEM_PROMPT}, *messages])
    data = parse_reply(raw)
    messages = [*messages, {"role": "assistant", "content": raw.strip()}]
    spec_data = data.get("spec")
    spec_text = spec_mod.format_spec(spec_data)
    if data["action"] == "continue":
        problems = spec_mod.validate(spec_data)
        if not problems:
            description = f"{data.get('full_description', '')}\n\n{spec_text}".strip()
            return {"messages": messages, "action": "continue", "description": description, "spec": spec_data}
        # The model confirmed too early: ask for what the specification still lacks instead of building.
        answer = "Before I start building, I still need: " + "; ".join(problems) + "."
        messages[-1] = {"role": "assistant", "content": json.dumps({"action": "reply", "answer": answer})}
        data = {"answer": answer}
        spec_text = spec_mod.format_spec(spec_data)
    answer = str(data.get("answer", ""))
    if spec_text:
        answer = f"{answer}\n\n{spec_text}"
    return {"messages": messages, "action": "reply", "answer": answer}


def fetch_sample(state: VSTInfo) -> dict:
    """Download the sample plugin sources and keep them in the state."""
    get_stream_writer()({"status": "Fetching sample"})
    return {"sample_code": fetch_sample_code()}


SEARCH_QUERIES_PROMPT = """You help write a JUCE 8 VST3 plugin. From the plugin description{error_hint} below, list up to 6 short
search queries (JUCE class names, methods or concepts) whose API documentation is needed to write the code
correctly. Answer only with a JSON array of strings.

Description:
{description}
{error}"""


def retrieve_docs(state: VSTInfo) -> dict:
    """Look up the JUCE documentation relevant to the plugin (and to the last build error) for write_code."""
    get_stream_writer()({"status": "Searching the JUCE docs"})
    error = state.get("build_error") or ""
    prompt = SEARCH_QUERIES_PROMPT.format(
        error_hint=" and the build errors" if error else "",
        description=state["description"],
        error=f"\nBuild errors:\n{error[:3000]}" if error else "",
    )
    try:
        text = call_openai([{"role": "user", "content": prompt}], temperature=0)
        queries = [str(q) for q in json.JSONDecoder().raw_decode(text[text.index("["):])[0]][:6]
    except Exception:
        queries = []
    queries = queries or [state["description"][:1000]]
    try:
        context = rag.retrieve(queries)
    except Exception:  # missing index or embedding failure: write the code without the docs
        context = ""
    if context:
        context = f"Relevant JUCE 8.0.8 API documentation (use it to get the signatures right):\n\n{context}\n\n"
    return {"rag_context": context}


def write_code(state: VSTInfo) -> dict:
    """Ask the model to write the plugin sources from the samples and the description."""
    if state.get("build_error"):
        get_stream_writer()({"status": "Build failed - fixing the code"})
    else:
        get_stream_writer()({"status": "Writing code"})
    previous_attempt = ""
    if state.get("build_error"):
        previous = state["generated_code"]
        files = "\n\n".join(f"{OUTPUT_FILES[k]}:\n{previous[k]}" for k in OUTPUT_FILES)
        previous_attempt = (
            "A previous attempt generated the following files:\n\n"
            f"{files}\n\n"
            "That attempt failed to build with the following errors:\n\n"
            f"{state['build_error']}\n\n"
            "Fix these errors. Return the complete corrected files.\n\n"
        )
    values = {**state["sample_code"], "description": state["description"], "rag_context": state.get("rag_context", ""), "previous_attempt": previous_attempt}
    # One pass, so braces inside the substituted text are never treated as placeholders.
    prompt = re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), WRITE_CODE_PROMPT)
    files, trace = agent.run(prompt, state["sample_code"], on_status=lambda text: get_stream_writer()({"status": text}))
    return {"generated_code": files, "agent_trace": [*(state.get("agent_trace") or []), *trace]}


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
    get_stream_writer()({"status": "Saving files"})
    project_dir = OUTPUT_DIR / uuid.uuid4().hex
    source_dir = project_dir / "Source"
    source_dir.mkdir(parents=True)
    (project_dir / "CMakeLists.txt").write_text(state["sample_code"]["cmake_lists"], encoding="utf-8")
    for key, filename in OUTPUT_FILES.items():
        (source_dir / filename).write_text(state["generated_code"][key], encoding="utf-8")
    return {"output_dir": str(project_dir)}


def build_plugin(state: VSTInfo) -> dict:
    """Push the project to a GitHub branch and trigger the Visual Studio build workflow."""
    get_stream_writer()({"status": "Building plugin"})
    branch = f"build/{Path(state['output_dir']).name}"
    url = trigger_build(state["output_dir"], branch)
    return {
        "build_branch": branch,
        "build_url": url,
        "build_attempts": state.get("build_attempts", 0) + 1,
    }


BUILD_TIMEOUT_MINUTES = 20
MAX_BUILD_ATTEMPTS = int(os.getenv("MAX_BUILD_ATTEMPTS", "3"))


def wait_for_build(state: VSTInfo) -> dict:
    """Wait (up to 20 minutes) for the GitHub Actions build and record the outcome."""
    writer = get_stream_writer()
    attempt = f"attempt {state['build_attempts']}/{MAX_BUILD_ATTEMPTS}"
    writer({"status": f"Waiting for build ({attempt})"})
    result = poll_build(
        state["build_branch"],
        BUILD_TIMEOUT_MINUTES * 60,
        on_wait=lambda secs: writer({"status": f"Waiting for build ({attempt}, {secs // 60} min)"}),
    )
    update = {"build_status": result["status"], "build_url": result["url"] or state["build_url"]}
    if result["status"] == "success":
        update["build_error"] = ""
        writer({"status": "Downloading plugin"})
        try:
            update["plugin_zip"] = download_plugin(result["run_id"], Path(state["output_dir"]) / "vst3.zip")
            update["build_message"] = "Build succeeded! Your VST3 plugin is ready - download it below."
        except (RuntimeError, httpx.HTTPError) as e:
            update["build_message"] = (
                f"The build succeeded, but the plugin could not be downloaded ({e}). "
                f"You can get it from the Artifacts section of {result['url']}"
            )
    else:
        update["build_error"] = result["error"]
    return update


def route_after_build(state: VSTInfo) -> str:
    if state["build_status"] == "success":
        return "done"
    if state["build_status"] == "failed" and state["build_attempts"] < MAX_BUILD_ATTEMPTS:
        return "retry"
    return "give_up"


def give_up(state: VSTInfo) -> dict:
    if state["build_status"] == "timeout":
        why = f"The build did not finish within {BUILD_TIMEOUT_MINUTES} minutes."
    else:
        why = f"The build still failed after {state['build_attempts']} attempts.\n\n{state['build_error']}"
    return {"build_message": f"{why}\n\nDetails: {state['build_url']}"}


UI_QUESTION = "Do you have a picture of the UI design you want for the plugin? (yes or no)"
UI_PICTURE_PROMPT = "Great! Please attach the picture of your UI design (use the paperclip button)."
UI_PICTURE_AGAIN = "I still need the picture. Please attach it with the paperclip button."

YES_NO_PROMPT = """\
The user was asked whether they have a picture of the UI design they want for their audio plugin.
Decide from their answer whether they said yes or no.
Reply with exactly one lowercase word: yes or no."""

ANALYZE_UI_PROMPT = """\
You are a UI analyst for audio plugins. Describe the plugin user interface in the picture in as much detail as possible
so that a developer can recreate it: the window size and proportions, the layout and every panel or section,
each control (knobs, sliders, buttons, switches, meters, displays, drop-downs) with its label, position, relative size
and likely function, the colour palette, fonts, textures and overall visual style. Answer in plain text."""


def ask_ui(state: VSTInfo) -> dict:
    """Ask whether the user has a picture of the UI; the model decides if the answer is yes or no."""
    text, image = _unwrap(interrupt(UI_QUESTION))
    if image:  # they attached the picture right away: that is a yes
        return {"ui_choice": "yes", "ui_image": image}
    answer = call_openai(
        [{"role": "system", "content": YES_NO_PROMPT}, {"role": "user", "content": text}],
        temperature=0,
    )
    return {"ui_choice": "yes" if answer.strip().lower().startswith("yes") else "no"}


def route_after_ui_question(state: VSTInfo) -> str:
    return "yes" if state["ui_choice"] == "yes" else "no"


def ask_image(state: VSTInfo) -> dict:
    """Require a picture: keep asking until one is attached."""
    if state.get("ui_image"):
        return {}
    prompt = UI_PICTURE_PROMPT
    while True:
        _, image = _unwrap(interrupt(prompt))
        if image:
            return {"ui_image": image}
        prompt = UI_PICTURE_AGAIN


def analyze_ui(state: VSTInfo) -> dict:
    """Describe the UI picture and add the description to the plugin description."""
    get_stream_writer()({"status": "Analyzing the UI picture"})
    analysis = call_openai(
        [
            {"role": "system", "content": ANALYZE_UI_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Describe this plugin UI."},
                {"type": "image_url", "image_url": {"url": state["ui_image"]}},
            ]},
        ],
        temperature=0.2,
    ).strip()
    description = f"{state.get('description', '')}\n\nUI design (described from the user's picture):\n{analysis}"
    return {"description": description.strip(), "ui_image": ""}


def route_after_assistant(state: VSTInfo) -> str:
    return "continue" if state["action"] == "continue" else "reply"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_graph(checkpointer=None):
    builder = StateGraph(VSTInfo)
    builder.add_node("collect", collect)
    builder.add_node("assistant", assistant)
    builder.add_node("ask_ui", ask_ui)
    builder.add_node("ask_image", ask_image)
    builder.add_node("analyze_ui", analyze_ui)
    builder.add_node("fetch_sample", fetch_sample)
    builder.add_node("retrieve_docs", retrieve_docs)
    builder.add_node("write_code", write_code)
    builder.add_node("save_files", save_files)
    builder.add_node("build_plugin", build_plugin)
    builder.add_node("wait_for_build", wait_for_build)
    builder.add_node("give_up", give_up)
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "assistant")
    builder.add_conditional_edges(
        "assistant",
        route_after_assistant,
        {"reply": "collect", "continue": "ask_ui"},
    )
    builder.add_conditional_edges(
        "ask_ui",
        route_after_ui_question,
        {"yes": "ask_image", "no": "fetch_sample"},
    )
    builder.add_edge("ask_image", "analyze_ui")
    builder.add_edge("analyze_ui", "fetch_sample")
    builder.add_edge("fetch_sample", "retrieve_docs")
    builder.add_edge("retrieve_docs", "write_code")
    builder.add_edge("write_code", "save_files")
    builder.add_edge("save_files", "build_plugin")
    builder.add_edge("build_plugin", "wait_for_build")
    builder.add_conditional_edges(
        "wait_for_build",
        route_after_build,
        {"done": END, "retry": "retrieve_docs", "give_up": "give_up"},
    )
    builder.add_edge("give_up", END)
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
