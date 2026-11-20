"""Push a generated plugin project to a GitHub branch and trigger the VST3 build workflow."""

import os
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
