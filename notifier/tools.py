"""
LangGraph tools for detecting breaking API changes and notifying consumer repos.

GitHub Code Search rate limit: 30 req/min (authenticated).
The _throttle_search() function enforces this via a sliding-window approach.
"""
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Annotated, Any

import httpx
from langchain_core.tools import tool

from crawler.config import REPO_ROOT, load_consumer_registry, load_registry

GITHUB_API = "https://api.github.com"
_MAX_CONSUMER_REPOS = 20     # cap per company to stay within rate limits
_MAX_RETRIES = 3
_RETRY_BACKOFF = [1, 4, 16]  # seconds

# Sliding-window throttler for GitHub Code Search (30 req/min, keep 5 in reserve)
_SEARCH_RATE_LIMIT = 30
_SEARCH_WINDOW = 60.0
_SEARCH_MARGIN = 5
_search_timestamps: list[float] = []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _throttle_search() -> None:
    """Block until a Code Search request is within the rate limit budget."""
    now = time.monotonic()
    _search_timestamps[:] = [t for t in _search_timestamps if now - t < _SEARCH_WINDOW]
    allowed = _SEARCH_RATE_LIMIT - _SEARCH_MARGIN
    if len(_search_timestamps) >= allowed:
        sleep_for = _SEARCH_WINDOW - (now - _search_timestamps[0]) + 0.1
        if sleep_for > 0:
            time.sleep(sleep_for)
    _search_timestamps.append(time.monotonic())


def _github_headers(token: str | None = None) -> dict[str, str]:
    tok = token or os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return headers


def _get(url: str, params: dict | None = None, token: str | None = None) -> Any:
    """GET with retry on rate limit."""
    for backoff in _RETRY_BACKOFF:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=_github_headers(token), params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 403):
            retry_after = int(resp.headers.get("Retry-After", backoff))
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
    raise RuntimeError(f"GitHub API failed after retries: {url}")


def _suffix_for(spec_type: str) -> str:
    return {"openapi": ".json", "graphql": ".graphql", "grpc": ".proto"}.get(spec_type, ".json")


# ---------------------------------------------------------------------------
# Plain functions — used by both the LangGraph @tool wrappers and the
# deterministic runner directly.
# ---------------------------------------------------------------------------

def get_changed_specs_plain() -> list[dict]:
    """
    Run git diff HEAD~1 HEAD --name-only -- companies/ and return structured
    metadata for each changed spec file. Returns [] on first commit or no changes.
    """
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--name-only", "--", "companies/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    registry = load_registry()
    company_map = {c.name: c for c in registry.companies}

    changed = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = Path(line).parts  # ('companies', 'stripe', 'openapi', 'stripe.openapi.json')
        if len(parts) < 3:
            continue
        company_name = parts[1]
        spec_type = parts[2]
        display = company_map[company_name].display_name if company_name in company_map else company_name
        changed.append({
            "path": line,
            "company": company_name,
            "spec_type": spec_type,
            "display_name": display,
        })
    return changed


def detect_breaking_changes_plain(company: str, spec_type: str, changed_path: str) -> dict:
    """
    Compare old vs new version of a spec using the driftabot engine CLI.
    Old version retrieved from git history (HEAD~1).
    Never returns spec content — only a compact change summary.
    """
    engine_bin = os.environ.get("DRIFTABOT_ENGINE_PATH", "driftabot")

    old_result = subprocess.run(
        ["git", "show", f"HEAD~1:{changed_path}"],
        cwd=str(REPO_ROOT),
        capture_output=True,
    )
    if old_result.returncode != 0:
        return {"company": company, "spec_path": changed_path, "breaking_count": 0,
                "breaking_changes": [], "error": "HEAD~1 version not found (new file)"}

    new_path = REPO_ROOT / changed_path
    if not new_path.exists():
        return {"company": company, "spec_path": changed_path, "breaking_count": 0,
                "breaking_changes": [], "error": f"New spec not found: {changed_path}"}

    suffix = _suffix_for(spec_type)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as old_f:
        old_f.write(old_result.stdout)
        old_tmp = old_f.name

    try:
        proc = subprocess.run(
            [engine_bin, spec_type, "--base", old_tmp, "--head", str(new_path), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Exit 0 = success, exit 1 only with --fail-on-breaking (not used here)
        if proc.returncode not in (0, 1):
            return {"company": company, "spec_path": changed_path, "breaking_count": 0,
                    "breaking_changes": [], "error": f"Engine error (exit {proc.returncode}): {proc.stderr[:300]}"}

        diff = json.loads(proc.stdout)
        breaking = [
            {
                "type": c.get("type", ""),
                "severity": c.get("severity", ""),
                "path": c.get("path", ""),
                "method": c.get("method", ""),
                "location": c.get("location", ""),
                "description": c.get("description", ""),
            }
            for c in diff.get("changes", [])
            if c.get("severity") == "breaking"
        ]
        return {
            "company": company,
            "spec_path": changed_path,
            "spec_type": spec_type,
            "breaking_count": len(breaking),
            "breaking_changes": breaking,
            "error": None,
        }
    except json.JSONDecodeError as exc:
        return {"company": company, "spec_path": changed_path, "breaking_count": 0,
                "breaking_changes": [], "error": f"JSON parse error: {exc}"}
    except subprocess.TimeoutExpired:
        return {"company": company, "spec_path": changed_path, "breaking_count": 0,
                "breaking_changes": [], "error": "Engine timed out after 60s"}
    finally:
        os.unlink(old_tmp)


def search_consumer_repos_plain(company_name: str) -> list[dict]:
    """
    Return repos to notify for a given company.

    Always includes repos registered in consumers.yaml (opt-in, no cap).
    Then appends dynamically discovered repos via GitHub Code Search (capped
    at _MAX_CONSUMER_REPOS additional repos beyond the registered set).
    """
    # 1. Registered consumers — always included, not subject to the search cap
    consumer_registry = load_consumer_registry()
    registered = [
        {
            "full_name": c.repo,
            "description": "(registered consumer)",
            "html_url": f"https://github.com/{c.repo}",
            "registered": True,
        }
        for c in consumer_registry.consumers
        if company_name in c.companies
    ]

    seen: set[str] = {r["full_name"] for r in registered}
    repos: list[dict] = list(registered)

    # 2. Dynamic discovery via Code Search — up to _MAX_CONSUMER_REPOS additional
    registry = load_registry()
    company = next((c for c in registry.companies if c.name == company_name), None)
    if not company or not company.consumers:
        return repos

    discovery_cap = len(registered) + _MAX_CONSUMER_REPOS
    for consumer in company.consumers:
        if len(repos) >= discovery_cap:
            break
        _throttle_search()
        try:
            data = _get(
                f"{GITHUB_API}/search/code",
                params={"q": consumer.query, "per_page": 10},
            )
            for item in data.get("items", []):
                repo = item.get("repository", {})
                full_name = repo.get("full_name", "")
                if full_name and full_name not in seen:
                    seen.add(full_name)
                    repos.append({
                        "full_name": full_name,
                        "description": repo.get("description", ""),
                        "html_url": repo.get("html_url", ""),
                        "registered": False,
                    })
                    if len(repos) >= discovery_cap:
                        break
        except Exception:
            continue

    return repos


def check_consumer_usage_plain(
    repo_full_name: str,
    breaking_change_path: str,
    breaking_change_location: str,
    breaking_change_description: str,
) -> dict:
    """
    Search a specific repo for code referencing the breaking change.
    Returns {repo, affected: bool, matched_files: list[str], query_used: str}.
    """
    # Build search term from the most specific available field
    term = ""
    if breaking_change_path:
        # Strip path params: /v1/subscriptions/{id} → subscriptions
        simplified = re.sub(r"/\{[^}]+\}", "/", breaking_change_path).rstrip("/")
        segs = [s for s in simplified.split("/") if s and not s.isdigit()]
        if segs:
            term = segs[-1]
    if not term and breaking_change_location:
        parts = breaking_change_location.split(".")
        last = parts[-1]
        if last and not last.isdigit():
            term = last
    if not term:
        # Fall back to first meaningful word from description
        words = [w for w in re.split(r"\W+", breaking_change_description) if len(w) > 4]
        term = words[0] if words else ""

    if not term:
        return {"repo": repo_full_name, "affected": False, "matched_files": [], "query_used": ""}

    query = f'repo:{repo_full_name} "{term}"'
    _throttle_search()
    try:
        data = _get(f"{GITHUB_API}/search/code", params={"q": query, "per_page": 5})
        items = data.get("items", [])
        matched_files = [item["path"] for item in items]
        return {
            "repo": repo_full_name,
            "affected": len(matched_files) > 0,
            "matched_files": matched_files[:5],
            "query_used": query,
        }
    except Exception as exc:
        return {"repo": repo_full_name, "affected": False, "matched_files": [],
                "query_used": query, "error": str(exc)}


def create_issue_plain(repo_full_name: str, title: str, body: str) -> dict:
    """
    Create a GitHub issue using DRIFTABOT_TOKEN. Checks for duplicates first.
    Returns {status: "created"|"duplicate"|"error", url, error}.
    """
    token = os.environ.get("DRIFTABOT_TOKEN", "")
    if not token:
        return {"status": "error", "url": None, "error": "DRIFTABOT_TOKEN not set"}

    # Check for existing open issues with the same title to avoid duplicates
    try:
        existing = _get(
            f"{GITHUB_API}/repos/{repo_full_name}/issues",
            params={"state": "open", "per_page": 30, "creator": "driftabot-agent"},
            token=token,
        )
        for issue in existing:
            if issue.get("title") == title:
                return {"status": "duplicate", "url": issue["html_url"], "error": None}
    except Exception:
        pass  # if check fails, proceed with creation

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{GITHUB_API}/repos/{repo_full_name}/issues",
            headers=_github_headers(token),
            json={"title": title, "body": body, "labels": ["api-breaking-change"]},
        )
    if resp.status_code == 201:
        return {"status": "created", "url": resp.json()["html_url"], "error": None}
    return {"status": "error", "url": None,
            "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}


# ---------------------------------------------------------------------------
# LangGraph @tool wrappers
# ---------------------------------------------------------------------------

@tool
def get_changed_specs() -> str:
    """
    Detect which spec files changed in the latest commit (HEAD~1 → HEAD).
    Returns a JSON array of {path, company, spec_type, display_name} objects.
    Returns [] if no spec files changed or this is the first commit.
    Never returns spec file contents.
    """
    return json.dumps(get_changed_specs_plain())


@tool
def detect_breaking_changes(
    company: Annotated[str, "Company name, e.g. 'stripe'"],
    spec_type: Annotated[str, "Spec type: 'openapi', 'graphql', or 'grpc'"],
    changed_path: Annotated[str, "Relative path to the changed spec, e.g. 'companies/stripe/openapi/stripe.openapi.json'"],
) -> str:
    """
    Compare old vs new version of a spec file using the driftabot engine.
    The old version is retrieved from git history (HEAD~1).
    Returns a JSON object with:
      - company, spec_path, spec_type
      - breaking_count: number of breaking changes found
      - breaking_changes: list of {type, path, method, location, description}
      - error: null or error message
    Never returns spec file contents — only the change summary.
    """
    return json.dumps(detect_breaking_changes_plain(company, spec_type, changed_path))


@tool
def search_consumer_repos(
    company_name: Annotated[str, "Company name from companies.yaml, e.g. 'stripe'"],
) -> str:
    """
    Find public GitHub repos that import this company's API client libraries.
    Uses the consumer search queries defined in companies.yaml.
    Returns a JSON array of {full_name, description, html_url}.
    Capped at 20 repos per company.
    """
    return json.dumps(search_consumer_repos_plain(company_name))


@tool
def check_consumer_usage(
    repo_full_name: Annotated[str, "Repo in 'owner/repo' format"],
    breaking_change_path: Annotated[str, "The path field from detect_breaking_changes (e.g. '/v1/subscriptions/{id}')"],
    breaking_change_location: Annotated[str, "The location field (e.g. 'request.body.email')"],
    breaking_change_description: Annotated[str, "Human-readable description of the breaking change"],
) -> str:
    """
    Search a consumer repo for code that references a specific breaking change.
    Returns a JSON object with:
      - repo, affected (bool), matched_files (list of file paths), query_used
    Only call this for repos found via search_consumer_repos.
    """
    return json.dumps(check_consumer_usage_plain(
        repo_full_name, breaking_change_path, breaking_change_location, breaking_change_description
    ))


@tool
def create_issue(
    repo_full_name: Annotated[str, "Repo in 'owner/repo' format"],
    title: Annotated[str, "Issue title"],
    body: Annotated[str, "Issue body in Markdown"],
) -> str:
    """
    Create a GitHub issue in a consumer repo using the driftbot account (DRIFTABOT_TOKEN).
    Checks for duplicate open issues before creating.
    Returns a JSON object with:
      - status: "created" | "duplicate" | "error"
      - url: issue URL if created or already exists
      - error: error message if status is "error"
    """
    return json.dumps(create_issue_plain(repo_full_name, title, body))


ALL_TOOLS = [
    get_changed_specs,
    detect_breaking_changes,
    search_consumer_repos,
    check_consumer_usage,
    create_issue,
]
