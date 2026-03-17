"""
Deterministic consumer notifier — no LLM required.

run_discover() — find new consumer repos (>=100 stars), scan them, register all, write pass/fail.
run_scan()     — sync consumer.companies.yaml from companies/consumers/, then scan all, write pass/fail.
"""
import json

from checker.__main__ import check as check_repo
from crawler.config import REPO_ROOT, load_consumer_registry, load_registry, register_consumer
from notifier.tools import search_consumer_repos_plain

_MAX_DISCOVER_REPOS = 20  # cap for open-ended GitHub discovery only


def _consumers_from_fs() -> dict[str, set[str]]:
    """
    Return {owner/repo: {company_slugs}} derived from companies/consumers/ JSON files.
    Handles the display-name → slug mapping (e.g. "Stripe" → "stripe").
    """
    registry = load_registry()
    slug_set = {c.name for c in registry.companies}
    display_to_slug = {c.display_name.lower(): c.name for c in registry.companies}

    result: dict[str, set[str]] = {}
    consumers_dir = REPO_ROOT / "companies" / "consumers"
    for bucket in ("pass", "fail"):
        bucket_dir = consumers_dir / bucket
        if not bucket_dir.exists():
            continue
        for owner_dir in bucket_dir.iterdir():
            if not owner_dir.is_dir():
                continue
            for repo_dir in owner_dir.iterdir():
                if not repo_dir.is_dir():
                    continue
                repo = f"{owner_dir.name}/{repo_dir.name}"
                for json_file in repo_dir.glob("*.json"):
                    try:
                        data = json.loads(json_file.read_text())
                        raw = data.get("company", "")
                        # Try lowercase slug match first ("Stripe" → "stripe"),
                        # then fall back to display-name lookup.
                        slug = (
                            raw.lower() if raw.lower() in slug_set
                            else display_to_slug.get(raw.lower())
                        )
                        if slug:
                            result.setdefault(repo, set()).add(slug)
                    except Exception:
                        pass
    return result


def _sync_consumer_yaml_from_fs() -> None:
    """
    Add to consumer.companies.yaml any repos found in companies/consumers/ that are
    not yet registered there. companies/consumers/ is the source of truth.
    """
    fs_consumers = _consumers_from_fs()
    consumer_registry = load_consumer_registry()
    yaml_repos = {entry.repo for entry in consumer_registry.consumers}

    added = 0
    for repo, companies in sorted(fs_consumers.items()):
        if repo not in yaml_repos:
            for company in sorted(companies):
                register_consumer(repo, company)
                added += 1
            print(f"  [sync] registered {repo} ({', '.join(sorted(companies))})")

    if added:
        print(f"  Synced {added} consumer(s) from companies/consumers/ → consumer.companies.yaml")


def run_discover() -> None:
    """Discover new consumer repos, scan each one, register all, write pass/fail."""
    registry = load_registry()
    consumer_registry = load_consumer_registry()
    # Known = union of YAML registry + anything already in companies/consumers/
    known: set[str] = (
        {entry.repo for entry in consumer_registry.consumers}
        | set(_consumers_from_fs().keys())
    )

    checked = 0
    for cfg in registry.companies:
        if checked >= _MAX_DISCOVER_REPOS:
            print(f"Run cap reached ({_MAX_DISCOVER_REPOS} repos). Stopping.")
            break
        repos = search_consumer_repos_plain(cfg.name)
        new_repos = [r for r in repos if r["full_name"] not in known]
        if not new_repos:
            continue
        print(f"\n[discover] {cfg.display_name}: {len(new_repos)} new candidate(s)")
        for repo in new_repos:
            if checked >= _MAX_DISCOVER_REPOS:
                print(f"Run cap reached ({_MAX_DISCOVER_REPOS} repos). Stopping.")
                break
            print(f"  Checking {repo['full_name']}...")
            check_repo(repo["full_name"], cfg.name, raise_issue=True)
            checked += 1
            register_consumer(repo["full_name"], cfg.name)
            known.add(repo["full_name"])

    print(f"\nDiscover done — repos checked: {checked}")


def run_scan() -> None:
    """Sync consumer.companies.yaml from companies/consumers/, then scan all registered consumers."""
    print("Syncing consumer.companies.yaml from companies/consumers/...")
    _sync_consumer_yaml_from_fs()

    consumer_registry = load_consumer_registry()
    if not consumer_registry.consumers:
        print("No registered consumers. Done.")
        return

    checked = 0
    for entry in consumer_registry.consumers:
        for company in entry.companies:
            print(f"  {entry.repo} → {company}")
            check_repo(entry.repo, company, raise_issue=True)
            checked += 1

    print(f"\nScan done — repos checked: {checked}")
