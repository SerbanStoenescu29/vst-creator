"""Push a generated plugin project to a GitHub branch and trigger the VST3 build workflow."""

import os
import re
import time
from pathlib import Path

import httpx

API = "https://api.github.com"


def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set (needs contents:write and actions:write)")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _post(url: str, payload: dict) -> httpx.Response:
    response = httpx.post(url, headers=_headers(), json=payload, timeout=60)
    if response.status_code >= 400:
        raise RuntimeError(f"GitHub {url} -> {response.status_code}: {response.text}")
    return response


def trigger_build(project_dir: str, branch: str) -> str:
    """Commit every file under project_dir to a new parentless branch `branch`
    of GITHUB_REPO, then dispatch the build-vst.yml workflow against it.
    Returns the Actions page URL."""
    repo = os.getenv("GITHUB_REPO", "SerbanStoenescu29/vst-creator")
    workflow = os.getenv("GITHUB_BUILD_WORKFLOW", "build-vst.yml")
    workflow_ref = os.getenv("GITHUB_WORKFLOW_REF", "master")
    root = Path(project_dir)

    tree = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        blob = _post(
            f"{API}/repos/{repo}/git/blobs",
            {"content": path.read_text(encoding="utf-8"), "encoding": "utf-8"},
        ).json()
        tree.append(
            {"path": path.relative_to(root).as_posix(), "mode": "100644", "type": "blob", "sha": blob["sha"]}
        )

    tree_sha = _post(f"{API}/repos/{repo}/git/trees", {"tree": tree}).json()["sha"]
    commit_sha = _post(
        f"{API}/repos/{repo}/git/commits",
        {"message": f"Generated plugin {branch}", "tree": tree_sha, "parents": []},
    ).json()["sha"]
    _post(f"{API}/repos/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": commit_sha})

    _post(
        f"{API}/repos/{repo}/actions/workflows/{workflow}/dispatches",
        {"ref": workflow_ref, "inputs": {"branch": branch}},
    )
    return f"https://github.com/{repo}/actions/workflows/{workflow}"


POLL_SECONDS = int(os.getenv("BUILD_POLL_SECONDS", "15"))


def _get(url: str, **kwargs) -> httpx.Response:
    response = httpx.get(url, headers=_headers(), timeout=60, follow_redirects=True, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"GitHub {url} -> {response.status_code}: {response.text[:300]}")
    return response


def _find_run(repo: str, workflow: str, branch: str) -> dict | None:
    """The run started for `branch` is the one whose run-name is 'Build <branch>'."""
    runs = _get(
        f"{API}/repos/{repo}/actions/workflows/{workflow}/runs",
        params={"event": "workflow_dispatch", "per_page": 30},
    ).json()["workflow_runs"]
    return next((r for r in runs if r.get("display_title") == f"Build {branch}"), None)


def _error_excerpt(repo: str, run_id: int, max_lines: int = 60) -> str:
    """Pull the compiler/CMake error lines out of the failed job's log."""
    jobs = _get(f"{API}/repos/{repo}/actions/runs/{run_id}/jobs").json()["jobs"]
    lines = []
    for job in jobs:
        if job.get("conclusion") != "failure":
            continue
        log = _get(f"{API}/repos/{repo}/actions/jobs/{job['id']}/logs").text
        for line in log.splitlines():
            line = line.split("Z ", 1)[1] if line[:4].isdigit() and "Z " in line[:40] else line
            if re.search(r"error|fatal|failed", line, re.I) and line not in lines:
                lines.append(line.strip())
        if not lines:  # no recognisable error lines: fall back to the end of the log
            lines = [l.strip() for l in log.splitlines()[-max_lines:]]
    return "\n".join(lines[:max_lines]) or "The build failed, but no log output could be read."


def wait_for_build(branch: str, timeout_seconds: int = 20 * 60, on_wait=None) -> dict:
    """Poll until the workflow run for `branch` finishes or the timeout passes.

    Returns {"status": "success" | "failed" | "timeout", "url": ..., "error": ...}.
    """
    repo = os.getenv("GITHUB_REPO", "SerbanStoenescu29/vst-creator")
    workflow = os.getenv("GITHUB_BUILD_WORKFLOW", "build-vst.yml")
    started = time.monotonic()
    run = None
    while time.monotonic() - started < timeout_seconds:
        run = _find_run(repo, workflow, branch)
        if run and run["status"] == "completed":
            if run["conclusion"] == "success":
                return {"status": "success", "url": run["html_url"], "run_id": run["id"], "error": ""}
            return {"status": "failed", "url": run["html_url"], "run_id": run["id"], "error": _error_excerpt(repo, run["id"])}
        if on_wait:
            on_wait(int(time.monotonic() - started))
        time.sleep(POLL_SECONDS)
    return {
        "status": "timeout",
        "url": run["html_url"] if run else "",
        "error": f"The build did not finish within {timeout_seconds // 60} minutes.",
    }


def download_plugin(run_id: int, dest: Path) -> str:
    """Download the build's VST3 artifact (a zip) from the finished run to `dest`."""
    repo = os.getenv("GITHUB_REPO", "SerbanStoenescu29/vst-creator")
    artifacts = _get(f"{API}/repos/{repo}/actions/runs/{run_id}/artifacts").json()["artifacts"]
    if not artifacts:
        raise RuntimeError("the run produced no artifact")
    # The API redirects to short-lived storage; httpx drops the token on that cross-origin hop.
    data = _get(f"{API}/repos/{repo}/actions/artifacts/{artifacts[0]['id']}/zip").content
    dest.write_bytes(data)
    return str(dest)
