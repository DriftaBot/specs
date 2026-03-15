"""
Discover new public API providers not yet in provider.companies.yaml.

Sources:
  1. APIs.guru  — curated list of ~2,500 public REST APIs, many sourced from GitHub.
  2. GitHub topic search — repos tagged with OpenAPI / GraphQL / gRPC topics.

Output: companies/discovery/candidates.json  (committed for human review).
"""
import json
import os
import re
import time
from datetime import datetime

import httpx

from crawler.config import REPO_ROOT, load_registry

APIS_GURU_URL = "https://api.apis.guru/v2/list.json"
GITHUB_API    = "https://api.github.com"

_MIN_STARS  = 500
# Balanced caps per spec type so all three categories appear in the output
_MAX_PER_TYPE: dict[str, int] = {
    "openapi":  60,
    "graphql":  20,
    "grpc":     20,
}

_OPENAPI_TOPICS = ["openapi-specification", "openapi", "swagger", "rest-api"]
_GRAPHQL_TOPICS = ["graphql-api", "graphql-schema", "graphql"]
_GRPC_TOPICS    = ["grpc", "protobuf", "protocol-buffers"]

# topic → spec_type (evaluated in order; first match wins per repo)
_TOPIC_SPEC_TYPE: dict[str, str] = (
    {t: "openapi" for t in _OPENAPI_TOPICS}
    | {t: "graphql" for t in _GRAPHQL_TOPICS}
    | {t: "grpc"    for t in _GRPC_TOPICS}
)
_ALL_TOPICS = list(_TOPIC_SPEC_TYPE)

_OUTPUT = REPO_ROOT / "companies" / "discovery" / "candidates.json"


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def _gh_headers() -> dict[str, str]:
    tok = os.environ.get("GITHUB_TOKEN", "")
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _gh_get(url: str, params: dict | None = None) -> dict:
    for delay in (1, 4, 16):
        with httpx.Client(timeout=30) as c:
            r = c.get(url, headers=_gh_headers(), params=params)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 403):
            time.sleep(int(r.headers.get("Retry-After", delay)))
            continue
        r.raise_for_status()
    raise RuntimeError(f"GitHub API failed after retries: {url}")


# ---------------------------------------------------------------------------
# Known-provider filtering
# ---------------------------------------------------------------------------

def _known_names(registry) -> set[str]:
    """Return lowercased name variants for every tracked provider."""
    names: set[str] = set()
    for c in registry.companies:
        names.add(c.name.lower())
        names.add(c.display_name.lower())
        names.add(f"{c.name.lower()}.com")
    return names


def _is_known(name: str, org: str, known: set[str]) -> bool:
    return any(x in known for x in (name, org, f"{name}.com", f"{org}.com"))


# ---------------------------------------------------------------------------
# Source 1: APIs.guru
# ---------------------------------------------------------------------------

def _github_repo_from_url(url: str) -> str | None:
    m = re.search(
        r"(?:github\.com|raw\.githubusercontent\.com)/([^/]+/[^/\s#?]+)", url
    )
    return m.group(1).rstrip("/") if m else None


def _discover_apis_guru(known: set[str]) -> list[dict]:
    """
    Fetch the APIs.guru list and return candidates whose spec is hosted on GitHub
    and whose provider name doesn't match a known company.
    APIs.guru only covers REST/OpenAPI, so spec_type is always 'openapi'.
    """
    print("Fetching APIs.guru list...")
    try:
        with httpx.Client(timeout=30) as c:
            r = c.get(APIS_GURU_URL)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        print(f"  [warning] APIs.guru unavailable: {exc}")
        return []

    candidates: list[dict] = []

    for api_key, api_info in data.items():
        # api_key examples: "stripe.com", "amazonaws.com:s3", "twilio.com"
        provider  = api_key.split(":")[0]
        base_name = provider.split(".")[0].lower()
        if _is_known(base_name, base_name, known) or provider.lower() in known:
            continue

        preferred = api_info.get("preferred", "")
        vinfo = api_info.get("versions", {}).get(preferred, {})
        if not vinfo:
            continue

        # Locate a GitHub source URL (x-origin list, or swaggerUrl / openApiUrl)
        github_repo: str | None = None
        spec_url:    str | None = None

        origins = vinfo.get("info", {}).get("x-origin", [])
        if isinstance(origins, dict):
            origins = [origins]
        for o in (origins or []):
            u = o.get("url", "")
            if "github" in u:
                github_repo = _github_repo_from_url(u)
                spec_url = u
                break

        if not github_repo:
            for key in ("swaggerUrl", "openApiUrl"):
                u = vinfo.get(key, "") or ""
                if "github" in u:
                    github_repo = _github_repo_from_url(u)
                    spec_url = u
                    break

        if not github_repo:
            continue  # skip APIs not sourced from GitHub

        info = vinfo.get("info", {})
        candidates.append({
            "name":        base_name,
            "provider":    provider,
            "title":       info.get("title", ""),
            "description": (info.get("description") or "")[:200],
            "github_repo": github_repo,
            "spec_url":    spec_url,
            "spec_type":   "openapi",
            "source":      "apis.guru",
        })

    print(f"  {len(candidates)} new candidates from APIs.guru")
    return candidates


# ---------------------------------------------------------------------------
# Source 2: GitHub topic search
# ---------------------------------------------------------------------------

def _infer_spec_type(repo_topics: list[str]) -> str:
    """Return the spec type inferred from a repo's GitHub topics."""
    for t in repo_topics:
        if t in _TOPIC_SPEC_TYPE:
            return _TOPIC_SPEC_TYPE[t]
    return "openapi"


def _discover_github_topics(known: set[str], seen_repos: set[str]) -> list[dict]:
    """
    Search GitHub for repos tagged with OpenAPI / GraphQL / gRPC topics.
    Covers all three spec types; infers spec_type from the matched topic.
    """
    candidates: list[dict] = []

    for topic in _ALL_TOPICS:
        print(f"  GitHub topic: {topic}...")
        try:
            data = _gh_get(
                f"{GITHUB_API}/search/repositories",
                params={
                    "q":        f"topic:{topic} stars:>{_MIN_STARS}",
                    "sort":     "stars",
                    "order":    "desc",
                    "per_page": 30,
                },
            )
        except Exception as exc:
            print(f"  [warning] topic search failed ({topic}): {exc}")
            time.sleep(2)
            continue

        for repo in data.get("items", []):
            full_name = repo.get("full_name", "")
            if full_name in seen_repos:
                continue

            org    = (repo.get("owner") or {}).get("login", "").lower()
            name   = repo.get("name", "").lower()
            topics = repo.get("topics", [])

            if _is_known(name, org, known):
                continue

            seen_repos.add(full_name)
            candidates.append({
                "name":        org,
                "provider":    f"{org}.com",
                "title":       (repo.get("description") or ""),
                "description": (repo.get("description") or "")[:200],
                "github_repo": full_name,
                "spec_url":    None,
                "spec_type":   _infer_spec_type(topics),
                "stars":       repo.get("stargazers_count", 0),
                "source":      "github_topics",
                "topics":      topics,
            })

        time.sleep(1)  # gentle pacing between topic searches

    print(f"  {len(candidates)} new candidates from GitHub topics")
    return candidates


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run() -> None:
    registry = load_registry()
    known    = _known_names(registry)
    print(f"Known providers: {len(registry.companies)}"
          f" ({', '.join(c.name for c in registry.companies)})")
    print()

    # Source 1: APIs.guru
    guru_candidates = _discover_apis_guru(known)
    seen_repos: set[str] = {c["github_repo"] for c in guru_candidates}

    # Source 2: GitHub topics (OpenAPI + GraphQL + gRPC)
    print("\nSearching GitHub topics...")
    gh_candidates = _discover_github_topics(known, seen_repos)

    all_candidates = guru_candidates + gh_candidates

    # Sort within each source: APIs.guru first (curated), then by stars descending
    all_candidates.sort(
        key=lambda c: (c["source"] != "apis.guru", -c.get("stars", 9999))
    )

    # Deduplicate by github_repo
    seen2: set[str] = set()
    deduped: list[dict] = []
    for c in all_candidates:
        key = c.get("github_repo") or c["provider"]
        if key not in seen2:
            seen2.add(key)
            deduped.append(c)

    # Select balanced top-N per spec type
    per_type: dict[str, list[dict]] = {t: [] for t in _MAX_PER_TYPE}
    for c in deduped:
        t = c.get("spec_type", "openapi")
        bucket = per_type.get(t, per_type["openapi"])
        cap = _MAX_PER_TYPE.get(t, _MAX_PER_TYPE["openapi"])
        if len(bucket) < cap:
            bucket.append(c)

    top = per_type["openapi"] + per_type["graphql"] + per_type["grpc"]
    total = sum(len(b) for b in per_type.values())
    print(f"\nTotal new candidates: {len(deduped)}, saving {total}"
          f" (openapi={len(per_type['openapi'])},"
          f" graphql={len(per_type['graphql'])},"
          f" grpc={len(per_type['grpc'])})")

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text(
        json.dumps(
            {
                "discovered_at":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "known_providers": len(registry.companies),
                "candidate_count": len(deduped),
                "by_type": {t: len(b) for t, b in per_type.items()},
                "candidates":      top,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Saved → {_OUTPUT.relative_to(REPO_ROOT)}")

    # Pretty-print top 10 for the workflow log
    print("\nTop 10 candidates:")
    for i, c in enumerate(top[:10], 1):
        stars     = f" ⭐{c['stars']}" if c.get("stars") else ""
        spec_type = c.get("spec_type", "")
        label     = c.get("title") or c["name"]
        print(f"  {i:2}. [{spec_type}] {label} ({c['github_repo']}){stars}")
