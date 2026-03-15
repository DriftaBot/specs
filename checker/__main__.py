"""
Consumer compatibility checker.

Checks whether a GitHub repo uses any endpoints from a company's API spec
and flags deprecated fields or removed endpoints.

Usage:
    python -m checker --repo spree/spree_stripe --company stripe
"""
import argparse
import json
import sys
from pathlib import Path

from crawler.config import REPO_ROOT, load_registry
from notifier.tools import GITHUB_API, _get, _throttle_search


def _load_spec(company: str) -> tuple[dict, str]:
    """Load the local OpenAPI spec for a company. Returns (spec, spec_path)."""
    openapi_dir = REPO_ROOT / "companies" / "providers" / company / "openapi"
    files = sorted(openapi_dir.glob("*.json"))
    if not files:
        print(f"No OpenAPI spec found for '{company}' at {openapi_dir}")
        sys.exit(1)
    path = files[0]
    return json.loads(path.read_text()), str(path.relative_to(REPO_ROOT))


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


def check(repo: str, company: str) -> None:
    registry = load_registry()
    company_cfg = next((c for c in registry.companies if c.name == company), None)
    if not company_cfg:
        print(f"Company '{company}' not found in provider.companies.yaml")
        sys.exit(1)

    spec, spec_path = _load_spec(company)
    resource_index = _build_resource_index(spec)

    display = company_cfg.display_name
    print(f"Checking  : {repo}")
    print(f"Against   : {display} OpenAPI spec ({spec_path})")
    print(f"Resources : {len(resource_index)} endpoint groups in spec")
    print()

    used = []
    not_used = []
    errors = []

    for resource, info in sorted(resource_index.items()):
        _throttle_search()
        try:
            data = _get(
                f"{GITHUB_API}/search/code",
                params={"q": f'repo:{repo} "{resource}"', "per_page": 5},
            )
            count = data.get("total_count", 0)
            if count > 0:
                files = [item["path"] for item in data.get("items", [])]
                used.append({
                    "resource": resource,
                    "count": count,
                    "files": files,
                    "deprecated_fields": info["deprecated_fields"],
                })
            else:
                not_used.append(resource)
        except Exception as exc:
            errors.append(f"{resource}: {exc}")

    # ── Report ────────────────────────────────────────────────────────────────
    issues = [r for r in used if r["deprecated_fields"]]

    print(f"Used  : {len(used)} resource(s)")
    print(f"Unused: {len(not_used)} resource(s)")
    if errors:
        print(f"Errors: {len(errors)}")
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
