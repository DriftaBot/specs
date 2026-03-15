"""
Deterministic consumer notifier — no LLM required.

Implements the same 5-phase flow as the agent: detect changed specs, detect
breaking changes, discover consumer repos, check usage, create issues.
Used as the fallback when ANTHROPIC_API_KEY is not set.
"""
from checker.__main__ import check as check_repo
from crawler.config import load_registry, register_consumer
from notifier.tools import (
    check_consumer_usage_plain,
    create_issue_plain,
    detect_breaking_changes_plain,
    get_changed_specs_plain,
    log_issue,
    search_consumer_repos_plain,
)


_ANSIBLE_ORGS = {"ansible-collections", "ansible", "ansible-community"}


def _ansible_component(matched_files: list[str]) -> str:
    """Extract Ansible component name from matched file paths."""
    plugin_dirs = {"modules", "lookup", "filter", "callback", "connection", "inventory", "vars"}
    for f in matched_files:
        parts = f.replace("\\", "/").split("/")
        if len(parts) >= 2 and parts[-2] in plugin_dirs:
            return parts[-1].removesuffix(".py")
    if matched_files:
        return matched_files[0].split("/")[-1].rsplit(".", 1)[0]
    return "unknown"


def _ecosystem_suffix(repo_full_name: str, matched_files: list[str]) -> str:
    """Return ecosystem-specific bot fields to append to the issue body."""
    org = repo_full_name.split("/")[0].lower()
    if org in _ANSIBLE_ORGS:
        component = _ansible_component(matched_files)
        return (
            "\n\n---\n\n"
            "##### ISSUE TYPE\n"
            "- Bug Report\n\n"
            "##### COMPONENT NAME\n"
            f"{component}\n\n"
            "##### ANSIBLE VERSION\n"
            "N/A — this is an upstream API compatibility issue, not Ansible version-specific\n"
        )
    return ""


def _issue_title(display_name: str, description: str) -> str:
    short = description[:80] + "..." if len(description) > 80 else description
    return f"[DriftaBot] Breaking change in {display_name} API: {short}"


def _issue_body(
    display_name: str,
    spec_type: str,
    bc: dict,
    matched_files: list[str],
    spec_path: str = "",
    commit_sha: str = "",
    repo_full_name: str = "",
) -> str:
    files_md = "\n".join(f"- `{f}`" for f in matched_files) or "_(no specific files identified)_"
    spec_link = ""
    if spec_path and commit_sha:
        url = f"https://github.com/DriftaBot/registry/blob/{commit_sha}/{spec_path}"
        spec_link = f"\n**Spec:** [{spec_path}]({url})\n"
    method = bc.get('method', '')
    path_str = f"`{bc.get('path', '')}`" + (f" `{method}`" if method else "")
    suffix = _ecosystem_suffix(repo_full_name, matched_files)
    return f"""## Breaking API Change — {display_name} API

**DriftaBot** detected a breaking change in the **{display_name}** API that may affect this repository.

### What changed
**{bc['description']}**

| | |
|---|---|
| **Type** | `{bc['type']}` |
| **Path** | {path_str} |
| **Location** | `{bc.get('location', '')}` |
| **Severity** | Breaking |
{spec_link}
### Files referencing this endpoint
{files_md}

### Next steps
1. Review the files listed above and update any references to the changed endpoint or field.
2. Check the {display_name} API changelog for migration guidance.

---
*Opened by [DriftaBot](https://github.com/DriftaBot/registry)*{suffix}"""


def _discover_new_consumers() -> None:
    """
    For every company: find repos not yet in consumer.companies.yaml (≥100 stars),
    check them against the current spec, and register + raise issue only if issues found.
    """
    registry = load_registry()
    for cfg in registry.companies:
        repos = search_consumer_repos_plain(cfg.name)
        new_repos = [r for r in repos if not r["registered"]]
        if not new_repos:
            continue
        print(f"\n[discover] {cfg.display_name}: {len(new_repos)} new candidate(s)")
        for repo in new_repos:
            print(f"  Checking {repo['full_name']}...")
            issues_found = check_repo(repo["full_name"], cfg.name, raise_issue=True)
            if issues_found:
                register_consumer(repo["full_name"], cfg.name)
            else:
                print(f"  [skip] {repo['full_name']} — no issues detected")


def run() -> None:
    # Phase 0: discover and check new consumer repos across all companies
    _discover_new_consumers()

    # Phase 1: detect changed specs
    changed = get_changed_specs_plain()
    if not changed:
        print("No spec changes detected. Notifier exiting.")
        return

    print(f"Detected {len(changed)} changed spec file(s).")

    total_breaking = 0
    total_repos = 0
    total_affected = 0
    total_created = 0
    total_errors = 0

    # Group breaking changes by company (Phase 2)
    companies_breaks: dict[str, dict] = {}  # company_name -> {display_name, spec_type, changes}
    for entry in changed:
        result = detect_breaking_changes_plain(entry["company"], entry["spec_type"], entry["path"])
        if result.get("error"):
            print(f"  [error] {entry['company']}: {result['error']}")
            continue
        if result["breaking_count"] == 0:
            print(f"  [no breaks] {entry['path']}")
            continue
        print(f"  [breaking] {entry['path']}: {result['breaking_count']} breaking change(s)")
        total_breaking += result["breaking_count"]
        key = entry["company"]
        if key not in companies_breaks:
            companies_breaks[key] = {
                "display_name": entry["display_name"],
                "spec_type": entry["spec_type"],
                "spec_path": entry["path"],
                "commit_sha": entry.get("commit_sha", ""),
                "changes": [],
            }
        companies_breaks[key]["changes"].extend(result["breaking_changes"])

    # Phases 3–5: per-company loop
    for company_name, info in companies_breaks.items():
        display = info["display_name"]
        spec_type = info["spec_type"]
        spec_path = info["spec_path"]
        commit_sha = info["commit_sha"]
        breaking_changes = info["changes"]

        # Phase 3: find consumer repos
        repos = search_consumer_repos_plain(company_name)
        total_repos += len(repos)
        print(f"  [consumers] {company_name}: {len(repos)} repo(s) found")

        for repo in repos:
            for bc in breaking_changes:
                # Phase 4: check if repo uses the affected feature
                usage = check_consumer_usage_plain(
                    repo["full_name"],
                    bc.get("path", ""),
                    bc.get("location", ""),
                    bc.get("description", ""),
                )
                if not usage.get("affected"):
                    continue
                total_affected += 1

                # Phase 5: create issue
                title = _issue_title(display, bc["description"])
                body = _issue_body(display, spec_type, bc, usage["matched_files"], spec_path, commit_sha, repo["full_name"])
                result = create_issue_plain(repo["full_name"], title, body)
                if result["status"] == "created":
                    total_created += 1
                    print(f"  [issue created] {repo['full_name']}: {result['url']}")
                elif result["status"] == "duplicate":
                    print(f"  [duplicate]     {repo['full_name']}: {result['url']}")
                else:
                    total_errors += 1
                    print(f"  [error]         {repo['full_name']}: {result.get('error')}")
                    continue

                if result.get("url"):
                    log_issue(repo["full_name"], result["url"], title, company_name, result["status"])

    print(
        f"\nDone — breaking changes: {total_breaking}, "
        f"consumer repos found: {total_repos}, "
        f"affected: {total_affected}, "
        f"issues created: {total_created}, "
        f"errors: {total_errors}"
    )
