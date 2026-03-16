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
import re
import sys

from pydantic import BaseModel

from crawler.config import REPO_ROOT, load_registry, register_consumer
from notifier.tools import GITHUB_API, _get, _throttle_search, log_issue


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


def _url_in_spec(url_path: str, spec_paths: list[str]) -> bool:
    """Check if a URL path matches any spec path (handles {param} wildcards)."""
    path = url_path.split("?")[0]
    # Strip scheme+host: "https://api.sendgrid.com/api/mail.send.json" -> "/api/mail.send.json"
    if "://" in path:
        try:
            path = "/" + path.split("/", 3)[3]
        except IndexError:
            return False
    if not path.startswith("/"):
        path = "/" + path
    for spec_path in spec_paths:
        # Split on {param} BEFORE escaping so literal segments are escaped correctly.
        # (re.escape first would turn { } into \{ \}, breaking the substitution.)
        parts = re.split(r"\{[^}]+\}", spec_path)
        pattern = "[^/]+".join(re.escape(p) for p in parts)
        if re.fullmatch(pattern, path):
            return True
    return False


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
    endpoint_urls: list[str]  # path portions of API URLs found in code, e.g. "/api/mail.send.json"


def _analyze_file_with_claude(
    company: str,
    display_name: str,
    resource_names: list[str],
    file_path: str,
    content: str,
) -> _FileAnalysis:
    """
    Use Claude to determine if a file actually uses the company's API,
    which API resources it references, and which endpoint URL paths it calls.
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
            f"If uses_api=true:\n"
            f"1. Return the subset of the provided resource names genuinely referenced as "
            f"{display_name} API calls or SDK method calls. Only include resources that appear "
            f"as actual API interactions, not incidental string matches.\n"
            f"2. Extract API endpoint URL paths that appear as explicit string literals or "
            f"f-string/template constructions in HTTP client calls in the code. "
            f"Return only the path portion (e.g. \"/api/mail.send.json\", \"/v3/mail/send\") — "
            f"strip the scheme and host. "
            f"Do NOT include OAuth/authentication-flow endpoints, webhook callback URLs, or paths "
            f"inferred solely from SDK method names with no explicit URL string present."
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


def _build_issue(
    display: str,
    spec_path: str,
    used: list[dict],
    issues_removed: list[dict],
) -> tuple[str, str]:
    """Build GitHub issue title and body for detected problems."""
    problems = []
    for item in [r for r in used if r["deprecated_fields"]]:
        for dep in item["deprecated_fields"]:
            problems.append(f"`{dep}` — deprecated field")
    for item in issues_removed:
        problems.append(f"`{item['url']}`")

    short = problems[0][:80] if problems else "breaking changes detected"
    title = f"[DriftaBot] Breaking change in {display} API: {short}"

    rows = "\n".join(f"| `{p}` |" for p in problems)
    all_files: list[str] = []
    for item in [r for r in used if r["deprecated_fields"]]:
        all_files.extend(item["files"])
    for item in issues_removed:
        all_files.extend(item["files"])
    unique_files = list(dict.fromkeys(all_files))
    files_md = "\n".join(f"- `{f}`" for f in unique_files) or "_(no specific files identified)_"

    deprecated_section = ""
    for item in [r for r in used if r["deprecated_fields"]]:
        deprecated_section += f"\n**Resource `{item['resource']}`** — deprecated fields:\n"
        for dep in item["deprecated_fields"]:
            deprecated_section += f"- `{dep}`\n"

    removed_section = ""
    for item in issues_removed:
        removed_section += f"- `{item['url']}`\n"

    changes_md = ""
    if deprecated_section:
        changes_md += f"### Deprecated fields\n{deprecated_section}\n"
    if removed_section:
        changes_md += f"### Removed endpoints\n{removed_section}\n"

    body = f"""## Breaking API Change — {display} API

**DriftaBot** detected breaking changes in the **{display}** API that may affect this repository.

{changes_md}
### Affected files
{files_md}

### Next steps
1. Review the files listed above and update any references to the changed endpoints or fields.
2. Check the {display} API changelog for migration guidance.

---
*Opened by [DriftaBot](https://github.com/DriftaBot/registry)*"""

    return title, body


def check(repo: str, company: str, raise_issue: bool = False) -> bool:
    """Check repo against company spec. Returns True if issues were found."""
    registry = load_registry()
    company_cfg = next((c for c in registry.companies if c.name == company), None)
    if not company_cfg:
        print(f"Company '{company}' not found in provider.companies.yaml")
        return False

    spec, spec_path = _load_spec(company)
    resource_index = _build_resource_index(spec)
    spec_paths = list(spec.get("paths", {}).keys())

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
        return False

    total = data.get("total_count", 0)
    if total == 0:
        print(f"Result: No {display} API usage detected in {repo}.")
        if raise_issue:
            from notifier.tools import log_check_passed
            log_check_passed(repo, display)
        return False

    file_paths = [item["path"] for item in data.get("items", [])]
    print(f"Found {total} file(s) mentioning '{company}', fetching top {len(file_paths)}...")
    print()

    # ── Step 2: fetch file contents ───────────────────────────────────────────
    file_contents = _fetch_file_contents(repo, file_paths)

    used = []
    not_used = []
    resource_names = list(resource_index.keys())
    removed_url_files: dict[str, list[str]] = {}  # unrecognised URL -> [files]

    if use_claude:
        # ── Step 3a: Claude semantic analysis ────────────────────────────────
        confirmed_files: dict[str, list[str]] = {}  # path -> [resource names]

        for path, content in file_contents.items():
            analysis = _analyze_file_with_claude(
                company, display, resource_names, path, content
            )
            if not analysis.uses_api:
                continue

            valid = [r for r in analysis.resources if r in resource_index]
            confirmed_files[path] = valid

            # Check extracted URLs against spec — flag any not found
            for url in analysis.endpoint_urls:
                if url and not _url_in_spec(url, spec_paths):
                    removed_url_files.setdefault(url, []).append(path)

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
            if raise_issue:
                from notifier.tools import log_check_passed
                log_check_passed(repo, display)
            return False

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
    issues_deprecated = [r for r in used if r["deprecated_fields"]]
    issues_removed = [
        {"url": url, "files": files}
        for url, files in removed_url_files.items()
    ]

    print(f"Used    : {len(used)} resource(s)")
    if issues_removed:
        print(f"Removed : {len(issues_removed)} endpoint(s) not in current spec")
    print(f"Unused  : {len(not_used)} resource(s)")
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

    for item in issues_removed:
        print(f"  ✗ {item['url']}  — not in current spec (likely removed)")
        for f in item["files"][:3]:
            print(f"      {f}")

    print()
    if issues_deprecated or issues_removed:
        parts = []
        if issues_deprecated:
            parts.append(f"{len(issues_deprecated)} deprecated field(s)")
        if issues_removed:
            parts.append(f"{len(issues_removed)} removed endpoint(s)")
        print(f"Result: issue(s) found — {', '.join(parts)}.")

        if raise_issue:
            _raise_github_issue(repo, display, spec_path, used, issues_removed)

        return True
    elif not used:
        print(f"Result: No {display} API usage detected in {repo}.")
        if raise_issue:
            from notifier.tools import log_check_passed
            log_check_passed(repo, display)
    else:
        print(f"Result: OK — {len(used)} resource(s) used, all current.")
        if raise_issue:
            from notifier.tools import log_check_passed
            log_check_passed(repo, display)
    return False


def _raise_github_issue(
    repo: str,
    display: str,
    spec_path: str,
    used: list[dict],
    issues_removed: list[dict],
) -> None:
    """Open a GitHub issue on the consumer repo using DRIFTABOT_TOKEN."""
    from notifier.tools import create_issue_plain

    token = os.environ.get("DRIFTABOT_TOKEN")
    if not token:
        print("  [skip] DRIFTABOT_TOKEN not set — cannot raise issue.")
        return

    title, body = _build_issue(display, spec_path, used, issues_removed)

    result = create_issue_plain(repo, title, body, token=token)

    if result["status"] == "created":
        print(f"  [issue created] {result['url']}")
    elif result["status"] == "duplicate":
        print(f"  [duplicate]     {result['url']}")
    else:
        print(f"  [error]         {result.get('error')}")
        return

    if result.get("url"):
        log_issue(repo, result["url"], title, display, result["status"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Check a repo against a company API spec.")
    parser.add_argument("--repo", required=True, help="GitHub repo, e.g. spree/spree_stripe")
    parser.add_argument("--company", required=True, help="Company name, e.g. stripe")
    parser.add_argument("--raise-issue", action="store_true", help="Open a GitHub issue if problems are found")
    parser.add_argument("--add-consumer", action="store_true", help="Register repo in consumer.companies.yaml")
    args = parser.parse_args()
    issues_found = check(args.repo, args.company, raise_issue=args.raise_issue)
    if args.add_consumer:
        register_consumer(args.repo, args.company)
    if issues_found:
        sys.exit(1)


if __name__ == "__main__":
    main()
