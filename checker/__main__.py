"""
Consumer compatibility checker.

Checks whether a GitHub repo uses any endpoints from a company's API spec
and flags deprecated fields or removed endpoints.

Usage:
    python -m checker --repo spree/spree_stripe --company stripe
"""
import argparse
import json
import os
import sys
from pathlib import Path

from pydantic import BaseModel

from crawler.config import REPO_ROOT, load_registry
from notifier.tools import GITHUB_API, _get, _throttle_search


def _load_spec(company: str) -> tuple[dict, str]:
    """Load and merge all local OpenAPI specs for a company. Returns (merged_spec, spec_dir)."""
    openapi_dir = REPO_ROOT / "companies" / "providers" / company / "openapi"
    files = sorted(openapi_dir.glob("*.json"))
    if not files:
        print(f"No OpenAPI spec found for '{company}' at {openapi_dir}")
        sys.exit(1)
    merged: dict = {"paths": {}}
    for f in files:
        try:
            spec = json.loads(f.read_text())
            merged["paths"].update(spec.get("paths", {}))
        except Exception:
            pass
    return merged, str(openapi_dir.relative_to(REPO_ROOT))


def _build_resource_index(spec: dict) -> dict[str, dict]:
    """
    Build index: resource_name -> {endpoints: [...], deprecated_fields: [...]}
    Resource name = second path segment, e.g. /v1/payment_intents -> payment_intents
    """
    index: dict[str, dict] = {}
    for path, path_item in spec.get("paths", {}).items():
        parts = path.strip("/").split("/")
        if len(parts) < 2:
            continue
        resource = parts[1]
        if resource not in index:
            index[resource] = {"endpoints": [], "deprecated_fields": []}

        for method, op in path_item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            body = (
                op.get("requestBody", {})
                .get("content", {})
                .get("application/x-www-form-urlencoded", {})
            )
            props = body.get("schema", {}).get("properties", {})
            dep = [f for f, info in props.items() if isinstance(info, dict) and info.get("deprecated")]
            if dep:
                index[resource]["deprecated_fields"].extend(
                    [f"{method.upper()} {path} -> {f}" for f in dep]
                )
            index[resource]["endpoints"].append(f"{method.upper()} {path}")

    return index


def _fetch_file_contents(repo: str, file_paths: list[str]) -> dict[str, str]:
    """Fetch raw content for a list of file paths in a repo. Returns {path: content}."""
    contents: dict[str, str] = {}
    for file_path in file_paths:
        try:
            data = _get(f"{GITHUB_API}/repos/{repo}/contents/{file_path}")
            if isinstance(data, dict) and data.get("encoding") == "base64":
                import base64
                contents[file_path] = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        except Exception:
            pass
    return contents


class _FileAnalysis(BaseModel):
    uses_api: bool
    resources: list[str]


def _analyze_file_with_claude(
    company: str,
    display_name: str,
    resource_names: list[str],
    file_path: str,
    content: str,
) -> _FileAnalysis:
    """
    Use Claude to determine if a file actually uses the company's API
    and which API resources it references.
    """
    import anthropic

    client = anthropic.Anthropic()
    resource_list = "\n".join(f"- {r}" for r in resource_names)

    response = client.messages.parse(
        model="claude-opus-4-6",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system=(
            f"You are analyzing source code to determine genuine usage of the {display_name} API.\n\n"
            f"Return uses_api=true only if the file actually integrates with the {display_name} API "
            f"(HTTP calls, SDK imports, authentication, etc.). "
            f"Return uses_api=false if the word \"{company}\" appears only coincidentally "
            f"(e.g. a different technical concept sharing the same name).\n\n"
            f"If uses_api=true, also return the subset of the provided resource names that are "
            f"genuinely referenced as {display_name} API calls or SDK method calls in the file. "
            f"Only include resources that appear as actual API interactions, not incidental string matches."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"File: {file_path}\n\n"
                f"Known {display_name} API resources:\n{resource_list}\n\n"
                f"File content:\n```\n{content[:10000]}\n```"
            ),
        }],
        output_format=_FileAnalysis,
    )
    return response.parsed_output


def check(repo: str, company: str) -> None:
    registry = load_registry()
    company_cfg = next((c for c in registry.companies if c.name == company), None)
    if not company_cfg:
        print(f"Company '{company}' not found in provider.companies.yaml")
        sys.exit(1)

    spec, spec_path = _load_spec(company)
    resource_index = _build_resource_index(spec)

    display = company_cfg.display_name
    use_claude = bool(os.environ.get("ANTHROPIC_API_KEY"))

    print(f"Checking  : {repo}")
    print(f"Against   : {display} OpenAPI spec ({spec_path})")
    print(f"Resources : {len(resource_index)} endpoint groups in spec")
    print(f"Analysis  : {'Claude (semantic)' if use_claude else 'lexical (no ANTHROPIC_API_KEY)'}")
    print()

    # ── Step 1: one broad search to find files mentioning the company ─────────
    print(f"Searching for {display} usage in {repo}...")
    _throttle_search()
    try:
        data = _get(
            f"{GITHUB_API}/search/code",
            params={"q": f'repo:{repo} "{company}"', "per_page": 10},
        )
    except Exception as exc:
        print(f"Search failed: {exc}")
        sys.exit(1)

    total = data.get("total_count", 0)
    if total == 0:
        print(f"Result: No {display} API usage detected in {repo}.")
        return

    file_paths = [item["path"] for item in data.get("items", [])]
    print(f"Found {total} file(s) mentioning '{company}', fetching top {len(file_paths)}...")
    print()

    # ── Step 2: fetch file contents ───────────────────────────────────────────
    file_contents = _fetch_file_contents(repo, file_paths)

    used = []
    not_used = []
    resource_names = list(resource_index.keys())

    if use_claude:
        # ── Step 3a: Claude semantic analysis ────────────────────────────────
        # Per-file: confirm API usage and identify which resources are referenced.
        confirmed_files: dict[str, list[str]] = {}  # path -> [resource, ...]
        for path, content in file_contents.items():
            analysis = _analyze_file_with_claude(
                company, display, resource_names, path, content
            )
            if analysis.uses_api:
                # Normalise: keep only names that exist in the spec index
                valid = [r for r in analysis.resources if r in resource_index]
                confirmed_files[path] = valid

        for resource, info in sorted(resource_index.items()):
            matched_files = [p for p, res in confirmed_files.items() if resource in res]
            if matched_files:
                used.append({
                    "resource": resource,
                    "count": len(matched_files),
                    "files": matched_files,
                    "deprecated_fields": info["deprecated_fields"],
                })
            else:
                not_used.append(resource)

        if not confirmed_files:
            print(f"Result: No genuine {display} API usage detected in {repo}.")
            return

    else:
        # ── Step 3b: lexical substring matching (fallback) ────────────────────
        for resource, info in sorted(resource_index.items()):
            matched_files = [
                path for path, content in file_contents.items()
                if resource in content
            ]
            if matched_files:
                used.append({
                    "resource": resource,
                    "count": len(matched_files),
                    "files": matched_files,
                    "deprecated_fields": info["deprecated_fields"],
                })
            else:
                not_used.append(resource)

    # ── Report ────────────────────────────────────────────────────────────────
    issues = [r for r in used if r["deprecated_fields"]]

    print(f"Used  : {len(used)} resource(s)")
    print(f"Unused: {len(not_used)} resource(s)")
    print()

    for item in used:
        flag = "⚠ " if item["deprecated_fields"] else "✓ "
        print(f"  {flag}{item['resource']}  ({item['count']} file match(es))")
        for f in item["files"][:3]:
            print(f"      {f}")
        if item["deprecated_fields"]:
            print(f"      DEPRECATED FIELDS:")
            for dep in item["deprecated_fields"]:
                print(f"        - {dep}")

    print()
    if issues:
        print(f"Result: {len(issues)} issue(s) found — deprecated fields in use.")
        sys.exit(1)
    elif not used:
        print(f"Result: No {display} API usage detected in {repo}.")
    else:
        print(f"Result: OK — {len(used)} resource(s) used, all current.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check a repo against a company API spec.")
    parser.add_argument("--repo", required=True, help="GitHub repo, e.g. spree/spree_stripe")
    parser.add_argument("--company", required=True, help="Company name, e.g. stripe")
    args = parser.parse_args()
    check(args.repo, args.company)


if __name__ == "__main__":
    main()
