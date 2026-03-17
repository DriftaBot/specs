"""
LangGraph tools for checking consumer repos against current provider specs
and notifying them of incorrect/outdated API usage via GitHub issues.

GitHub Code Search rate limit: 30 req/min (authenticated).
The _throttle_search() function enforces this via a sliding-window approach.
"""
import json
import os
import time
from datetime import datetime
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

_MIN_CONSUMER_STARS = 100  # minimum stars for dynamically-discovered repos


def _repo_stars(repo: str) -> int:
    """Return the star count for a GitHub repo (0 on error)."""
    try:
        return _get(f"{GITHUB_API}/repos/{repo}").get("stargazers_count", 0)
    except Exception:
        return 0


def log_issue(repo: str, url: str, title: str, company: str, status: str) -> None:
    """Write a fail record to companies/consumers/fail/<owner>/<repo>/<number>.json."""
    try:
        issue_number = url.rstrip("/").split("/")[-1]
        owner, repo_name = repo.split("/", 1)
        log_dir = REPO_ROOT / "companies" / "consumers" / "fail" / owner / repo_name
        log_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "url": url,
            "title": title,
            "company": company,
            "status": status,
            "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        path = log_dir / f"{issue_number}.json"
        path.write_text(json.dumps(record, indent=2) + "\n")
        print(f"  [logged]  {path.relative_to(REPO_ROOT)}")
        badge = {"schemaVersion": 1, "label": "DriftaBot", "message": "Fail", "color": "red"}
        (log_dir / "badge.json").write_text(json.dumps(badge, indent=2) + "\n")
    except Exception as exc:
        print(f"  [log error] {exc}")


def log_check_passed(repo: str, company: str) -> None:
    """Write a pass record to companies/consumers/pass/<owner>/<repo>/status.json."""
    try:
        owner, repo_name = repo.split("/", 1)
        log_dir = REPO_ROOT / "companies" / "consumers" / "pass" / owner / repo_name
        log_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "repo": repo,
            "url": f"https://github.com/{repo}",
            "company": company,
            "status": "passed",
            "message": "No issues found with API",
            "checked_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        path = log_dir / "status.json"
        path.write_text(json.dumps(record, indent=2) + "\n")
        print(f"  [logged]  {path.relative_to(REPO_ROOT)}")
        badge = {"schemaVersion": 1, "label": "DriftaBot", "message": "Pass", "color": "brightgreen"}
        (log_dir / "badge.json").write_text(json.dumps(badge, indent=2) + "\n")
    except Exception as exc:
        print(f"  [log error] {exc}")


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


# ---------------------------------------------------------------------------
# Plain functions — used by both the LangGraph @tool wrappers and the
# deterministic runner directly.
# ---------------------------------------------------------------------------

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
                    if _repo_stars(full_name) < _MIN_CONSUMER_STARS:
                        continue
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


def close_open_issues_plain(repo: str, company_display: str, token: str | None = None) -> int:
    """
    Close any open DriftaBot drift issues for this company on the consumer repo.
    Posts a resolution comment with badge markdown before closing.
    Returns count of issues closed.
    """
    token = token or os.environ.get("DRIFTABOT_TOKEN", "")
    if not token:
        return 0
    try:
        issues = _get(
            f"{GITHUB_API}/repos/{repo}/issues",
            params={"state": "open", "per_page": 30, "creator": "driftabot-agent"},
            token=token,
        )
    except Exception:
        return 0

    owner, repo_name = repo.split("/", 1)
    badge_md = (
        f"[![DriftaBot](https://img.shields.io/endpoint?url="
        f"https://raw.githubusercontent.com/DriftaBot/registry/main/"
        f"companies/consumers/pass/{owner}/{repo_name}/badge.json)]"
        f"(https://driftabot.github.io/registry/)"
    )
    closed = 0
    for issue in issues:
        title = issue.get("title", "")
        if company_display not in title:
            continue
        number = issue["number"]
        comment = (
            f"**DriftaBot re-scanned this repository and found no {company_display} API drift.** "
            "Your API usage is up-to-date — closing this issue automatically.\n\n"
            "Add this badge to your README to show your DriftaBot status:\n\n"
            f"```markdown\n{badge_md}\n```\n\n"
            "---\n"
            "Opened automatically by [DriftaBot](https://driftabot.github.io/registry/)"
        )
        try:
            with httpx.Client(timeout=30) as client:
                client.post(
                    f"{GITHUB_API}/repos/{repo}/issues/{number}/comments",
                    headers=_github_headers(token),
                    json={"body": comment},
                )
                client.patch(
                    f"{GITHUB_API}/repos/{repo}/issues/{number}",
                    headers=_github_headers(token),
                    json={"state": "closed"},
                )
            closed += 1
            print(f"  [resolved] closed #{number}")
        except Exception as exc:
            print(f"  [close error] #{number}: {exc}")
    return closed


def notify_pass_plain(repo: str, company_display: str, token: str | None = None) -> bool:
    """
    Open a one-time 'All clear' issue with badge markdown on first-time pass.
    Duplicate-safe via create_issue_plain. Returns True if a new issue was opened.
    """
    token = token or os.environ.get("DRIFTABOT_TOKEN", "")
    if not token:
        return False
    owner, repo_name = repo.split("/", 1)
    badge_md = (
        f"[![DriftaBot](https://img.shields.io/endpoint?url="
        f"https://raw.githubusercontent.com/DriftaBot/registry/main/"
        f"companies/consumers/pass/{owner}/{repo_name}/badge.json)]"
        f"(https://driftabot.github.io/registry/)"
    )
    title = f"[DriftaBot] {company_display} API usage is up-to-date ✓"
    body = (
        f"DriftaBot scanned this repository and found no issues with your "
        f"{company_display} API usage.\n\n"
        "Add this badge to your README:\n\n"
        f"```markdown\n{badge_md}\n```\n\n"
        "---\n"
        "Opened automatically by [DriftaBot](https://driftabot.github.io/registry/)"
    )
    result = create_issue_plain(repo, title, body, token=token)
    return result["status"] == "created"


def create_issue_plain(repo_full_name: str, title: str, body: str, token: str | None = None) -> dict:
    """
    Create a GitHub issue using DRIFTABOT_TOKEN (or the supplied token).
    Checks for duplicates first.
    Returns {status: "created"|"duplicate"|"error", url, error}.
    """
    token = token or os.environ.get("DRIFTABOT_TOKEN", "")
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
            json={"title": title, "body": body},
        )
    if resp.status_code == 201:
        return {"status": "created", "url": resp.json()["html_url"], "error": None}
    return {"status": "error", "url": None,
            "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}


# ---------------------------------------------------------------------------
# LangGraph @tool wrappers
# ---------------------------------------------------------------------------

@tool
def search_consumer_repos(
    company_name: Annotated[str, "Company name from companies.yaml, e.g. 'stripe'"],
) -> str:
    """
    Find public GitHub repos that import this company's API client libraries.
    Uses the consumer search queries defined in companies.yaml.
    Returns a JSON array of {full_name, description, html_url, registered}.
    Capped at 20 dynamically discovered repos per company (registered repos always included).
    """
    return json.dumps(search_consumer_repos_plain(company_name))


@tool
def check_consumer_repo(
    repo_full_name: Annotated[str, "Repo in 'owner/repo' format, e.g. 'spree/spree_stripe'"],
    company: Annotated[str, "Company name from companies.yaml, e.g. 'stripe'"],
) -> str:
    """
    Check if a consumer repo has incorrect or outdated usage of a company's API.
    Compares the consumer's code against the current provider spec in companies/providers/.
    Raises a GitHub issue via DRIFTABOT_TOKEN if problems are found (duplicate-safe).
    Returns a JSON object with:
      - repo, company, issues_found (bool)
    """
    from checker.__main__ import check as _check
    issues_found = _check(repo_full_name, company, raise_issue=True)
    return json.dumps({"repo": repo_full_name, "company": company, "issues_found": issues_found})


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
    search_consumer_repos,
    check_consumer_repo,
    create_issue,
]
