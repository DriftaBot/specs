"""
LangGraph tools for fetching API specs from GitHub.

All GitHub API calls use the GITHUB_TOKEN env var for authentication.
Rate limit: ~5,000 req/hr with a PAT, 1,000 req/hr with GITHUB_TOKEN in Actions.
"""
import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Annotated, Any

import httpx
from langchain_core.tools import tool

from crawler.config import REPO_ROOT, load_registry

GITHUB_API = "https://api.github.com"
_MAX_RETRIES = 3
_RETRY_BACKOFF = [1, 4, 16]  # seconds


def _github_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(url: str, params: dict | None = None) -> Any:
    """GET from GitHub API with retry on rate limit."""
    for attempt, backoff in enumerate(_RETRY_BACKOFF):
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=_github_headers(), params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 403):
            retry_after = int(resp.headers.get("Retry-After", backoff))
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
    raise RuntimeError(f"GitHub API request failed after {_MAX_RETRIES} retries: {url}")


# ---------------------------------------------------------------------------
# Plain functions — used by both the deterministic runner and the @tool wrappers
# ---------------------------------------------------------------------------

def list_dir(repo: str, path: str) -> list[dict]:
    """Return list of file metadata dicts for all files in a repo directory."""
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    items = _get(url)
    return [
        {"name": item["name"], "path": item["path"], "type": item["type"], "sha": item["sha"]}
        for item in items
        if item["type"] == "file"
    ]


def fetch_file(repo: str, path: str) -> tuple[str, str]:
    """Fetch a file from GitHub. Returns (content, github_sha)."""
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    data = _get(url)

    if data.get("encoding") == "base64":
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    elif data.get("download_url"):
        with httpx.Client(timeout=60) as client:
            resp = client.get(data["download_url"], headers=_github_headers())
            resp.raise_for_status()
            content = resp.text
    else:
        raise ValueError(f"Cannot decode file content from {repo}/{path}")

    return content, data.get("sha", "")


def content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def existing_sha256(output_path: str) -> str | None:
    """Return SHA-256 of existing local file, or None if absent."""
    full_path = REPO_ROOT / output_path
    if not full_path.exists():
        return None
    return hashlib.sha256(full_path.read_bytes()).hexdigest()


def write_file(output_path: str, content: str) -> None:
    full_path = REPO_ROOT / output_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# LangGraph @tool wrappers — used by the ReAct agent
#
# Design constraint: tools NEVER return spec file content back to the model.
# Spec files can be megabytes each; returning them in tool messages would
# exhaust the 1M token context window within a few companies. Instead, all
# fetch+compare+write logic happens inside the tools and only small status
# metadata is returned to the agent.
# ---------------------------------------------------------------------------

@tool
def load_companies_config() -> str:
    """
    Load the companies registry from companies.yaml.
    Returns a JSON string listing all companies and their spec entries.
    """
    registry = load_registry()
    return registry.model_dump_json(indent=2)


@tool
def list_repo_directory(
    repo: Annotated[str, "GitHub repo in 'owner/repo' format"],
    path: Annotated[str, "Directory path within the repo to list"],
) -> str:
    """
    List files in a GitHub repository directory.
    Returns a JSON array of objects with 'name' and 'path' fields only.
    On error returns a JSON object with an 'error' field.
    """
    try:
        files = list_dir(repo, path)
        # Return only name+path — sha and type not needed by the agent
        return json.dumps([{"name": f["name"], "path": f["path"]} for f in files])
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool
def sync_spec(
    repo: Annotated[str, "GitHub repo in 'owner/repo' format"],
    repo_path: Annotated[str, "File path within the repo to fetch"],
    output_path: Annotated[str, "Output file path relative to repo root (e.g. companies/stripe/openapi/stripe.openapi.json)"],
) -> str:
    """
    Fetch a spec file from GitHub and save it locally if it has changed.
    Returns a JSON object with:
      - status: "updated" | "unchanged" | "error"
      - output_path: the local path written
      - error: error message if status is "error", otherwise null
    Spec content is NEVER included in the return value.
    """
    try:
        content, _ = fetch_file(repo, repo_path)
        if content_sha256(content) == existing_sha256(output_path):
            return json.dumps({"status": "unchanged", "output_path": output_path, "error": None})
        write_file(output_path, content)
        return json.dumps({"status": "updated", "output_path": output_path, "error": None})
    except Exception as exc:
        return json.dumps({"status": "error", "output_path": output_path, "error": str(exc)})


ALL_TOOLS = [load_companies_config, list_repo_directory, sync_spec]
