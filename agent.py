"""The code-writing agent: Claude decides which tools to call, then submits the plugin.

Tools:
    search_juce_docs  - look up JUCE 8.0.8 API documentation (RAG, see rag.py)
    get_sample_file   - read one of the sample project files again
    validate_code     - static checks on the four sources, before submitting
    submit_plugin     - hand in the finished files (ends the run; rejected if the checks fail)
"""

import os
import re

import resilience
from langsmith import traceable

import rag

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "12"))
FILE_KEYS = ["plugin_editor_h", "plugin_editor_cpp", "plugin_processor_h", "plugin_processor_cpp"]

_FILES_SCHEMA = {k: {"type": "string", "description": f"Complete content of {k}"} for k in FILE_KEYS}

TOOLS = [
    {
        "name": "search_juce_docs",
        "description": "Search the JUCE 8.0.8 API documentation. Use it before using a JUCE class or method "
        "you are not sure about, and to look up the signature behind a compiler error. Returns documentation excerpts.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Class name, method or concept, e.g. 'dsp::IIR::Coefficients makeLowPass'"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_sample_file",
        "description": "Return one of the sample project files again (cmake_lists, plugin_editor_h, plugin_editor_cpp, plugin_processor_h, plugin_processor_cpp).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "enum": ["cmake_lists", *FILE_KEYS]}},
            "required": ["name"],
        },
    },
    {
        "name": "validate_code",
        "description": "Run static checks on the four source files (required classes, balanced brackets, no new dependencies). "
        "Call it before submit_plugin.",
        "input_schema": {"type": "object", "properties": _FILES_SCHEMA, "required": FILE_KEYS},
    },
    {
        "name": "submit_plugin",
        "description": "Submit the finished plugin. Call it once, with the complete content of all four files. "
        "Be honest in ungrounded and assumptions: they are shown to the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                **_FILES_SCHEMA,
                "ungrounded": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JUCE classes, methods or facts you used but found no documentation for (empty if all were documented)",
                },
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Choices you made that the plugin description did not specify",
                },
            },
            "required": FILE_KEYS,
        },
    },
]

_STD_HEADER = re.compile(r"^[a-z_]+$")  # <vector>, <cmath>, ...


def validate(files: dict) -> list[str]:
    """Static checks on the generated sources. Returns the problems found (empty = fine)."""
    problems = []
    for key in FILE_KEYS:
        text = files.get(key)
        if not isinstance(text, str) or len(text.strip()) < 40:
            problems.append(f"{key} is missing or empty")
            continue
        for open_, close in ("{}", "()", "[]"):
            if text.count(open_) != text.count(close):
                problems.append(f"{key}: unbalanced {open_}{close} ({text.count(open_)} vs {text.count(close)})")
        for inc in re.findall(r"#include\s*<([^>]+)>", text):
            if not (inc.startswith("juce_") or inc == "JuceHeader.h" or _STD_HEADER.match(inc) or inc.endswith(".h") and "/" not in inc and inc[0].islower()):
                problems.append(f"{key}: unexpected include <{inc}> (no new dependencies allowed)")
    if not problems:
        if "createPluginFilter" not in files["plugin_processor_cpp"]:
            problems.append("plugin_processor_cpp must define createPluginFilter()")
        if "AudioProcessor" not in files["plugin_processor_h"]:
            problems.append("plugin_processor_h must declare a juce::AudioProcessor subclass")
        if "AudioProcessorEditor" not in files["plugin_editor_h"]:
            problems.append("plugin_editor_h must declare a juce::AudioProcessorEditor subclass")
    return problems


@traceable(run_type="llm", name="anthropic-agent", metadata={"ls_provider": "anthropic", "ls_model_name": MODEL})
def _call(system: str, messages: list) -> dict:
    response = resilience.post(
        os.getenv("ANTHROPIC_URL", "https://api.anthropic.com/v1/messages"),
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": MODEL, "max_tokens": 24000, "system": system, "messages": messages, "tools": TOOLS},
        timeout=600,
    )
    data = response.json()
    usage = data.get("usage") or {}
    data["usage_metadata"] = {
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
        "total_tokens": int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0)),
    }
    return data


def run(system: str, sample_code: dict, on_status=lambda text: None) -> tuple[dict, list, dict]:
    """Run the agent. Returns (the four files, a trace of the tool calls, {"ungrounded": [...], "assumptions": [...]}).

    A trace entry is {"tool", "input", "result"}, plus "sources" ([{"file", "score"}]) for documentation searches.
    """
    messages = [{"role": "user", "content": "Write the plugin now. Use the tools, then call submit_plugin."}]
    trace = []
    for _ in range(MAX_STEPS):
        reply = _call(system, messages)
        blocks = reply["content"]
        messages.append({"role": "assistant", "content": blocks})
        calls = [b for b in blocks if b.get("type") == "tool_use"]
        if not calls:
            messages.append({"role": "user", "content": "Call submit_plugin with the finished files."})
            continue
        results = []
        for call in calls:
            name, args = call["name"], call.get("input") or {}
            is_error = False
            sources = None
            if name == "search_juce_docs":
                on_status(f"Agent: searching the JUCE docs for \"{args.get('query', '')[:60]}\"")
                try:
                    out, sources = rag.search([str(args.get("query", ""))], per_query=5, max_chars=7000)
                    out = out or "No documentation found."
                except Exception as exc:
                    out, is_error = f"Search failed: {exc}", True
                summary = f"{out.count('[juce_')} excerpts"
            elif name == "get_sample_file":
                out = sample_code.get(args.get("name"), "") or "Unknown file."
                summary = str(args.get("name"))
            elif name in ("validate_code", "submit_plugin"):
                on_status("Agent: checking the code" if name == "validate_code" else "Agent: submitting the code")
                problems = validate(args)
                if name == "submit_plugin" and not problems:
                    trace.append({"tool": name, "input": "four files", "result": "accepted"})
                    notes = {k: [str(i) for i in args.get(k) or [] if str(i).strip()] for k in ("ungrounded", "assumptions")}
                    return {k: args[k] for k in FILE_KEYS}, trace, notes
                out = "OK, no problems found." if not problems else "Problems:\n- " + "\n- ".join(problems)
                is_error = bool(problems) and name == "submit_plugin"
                summary = "ok" if not problems else f"{len(problems)} problems"
            else:
                out, is_error, summary = f"Unknown tool {name}", True, "unknown tool"
            entry = {"tool": name, "input": str(args.get("query") or args.get("name") or "")[:120], "result": summary}
            if sources:
                entry["sources"] = sources
            trace.append(entry)
            results.append({"type": "tool_result", "tool_use_id": call["id"], "content": out, "is_error": is_error})
        messages.append({"role": "user", "content": results})
    raise RuntimeError(f"The code agent did not submit a plugin within {MAX_STEPS} steps")
