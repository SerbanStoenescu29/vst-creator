"""Fetch the JUCE sample plugin sources from the vstai GitHub repo."""

from urllib.parse import quote

import httpx

RAW_BASE = "https://raw.githubusercontent.com/SerbanStoenescu29/vstai/main/Sample%20code"

SAMPLE_FILES = {
    "cmake_lists": "CMakeLists.txt",
    "plugin_editor_cpp": "Source/PluginEditor.cpp",
    "plugin_editor_h": "Source/PluginEditor.h",
    "plugin_processor_cpp": "Source/PluginProcessor.cpp",
    "plugin_processor_h": "Source/PluginProcessor.h",
}


def fetch_file(path: str) -> str:
    """GET one file (path relative to 'Sample code/') and return its text."""
    response = httpx.get(f"{RAW_BASE}/{quote(path)}", timeout=30, follow_redirects=True)
    response.raise_for_status()
    return response.text


def fetch_sample_code() -> dict[str, str]:
    """Return {cmake_lists, plugin_editor_cpp, plugin_editor_h,
    plugin_processor_cpp, plugin_processor_h} mapped to each file's content."""
    return {key: fetch_file(path) for key, path in SAMPLE_FILES.items()}

