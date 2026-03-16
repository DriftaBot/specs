"""
Deterministic consumer notifier — no LLM required.

run_discover() — find new consumer repos (>=100 stars), check them, register if issues found.
run_scan()     — check all registered consumers, write pass/fail to companies/consumers/.
"""
from checker.__main__ import check as check_repo
from crawler.config import load_consumer_registry, load_registry, register_consumer
from notifier.tools import search_consumer_repos_plain

_MAX_REPOS = 20  # hard cap on total repos checked per run


def run_discover() -> None:
    """Discover new consumer repos not yet in consumer.companies.yaml and check them."""
    registry = load_registry()
    consumer_registry = load_consumer_registry()
    known: set[str] = {entry.repo for entry in consumer_registry.consumers}

    checked = 0
    for cfg in registry.companies:
        if checked >= _MAX_REPOS:
            print(f"Run cap reached ({_MAX_REPOS} repos). Stopping.")
            break
        repos = search_consumer_repos_plain(cfg.name)
        new_repos = [r for r in repos if r["full_name"] not in known]
        if not new_repos:
            continue
        print(f"\n[discover] {cfg.display_name}: {len(new_repos)} new candidate(s)")
        for repo in new_repos:
            if checked >= _MAX_REPOS:
                print(f"Run cap reached ({_MAX_REPOS} repos). Stopping.")
                break
            print(f"  Checking {repo['full_name']}...")
            issues_found = check_repo(repo["full_name"], cfg.name, raise_issue=True)
            checked += 1
            if issues_found:
                register_consumer(repo["full_name"], cfg.name)
                known.add(repo["full_name"])
            else:
                print(f"  [skip] {repo['full_name']} — no issues detected")

    print(f"\nDiscover done — repos checked: {checked}")


def run_scan() -> None:
    """Check all registered consumers against current provider specs; write pass/fail results."""
    consumer_registry = load_consumer_registry()
    if not consumer_registry.consumers:
        print("No registered consumers. Done.")
        return

    checked = 0
    for entry in consumer_registry.consumers:
        for company in entry.companies:
            if checked >= _MAX_REPOS:
                print(f"Run cap reached ({_MAX_REPOS} repos). Stopping.")
                return
            print(f"  {entry.repo} → {company}")
            check_repo(entry.repo, company, raise_issue=True)
            checked += 1

    print(f"\nScan done — repos checked: {checked}")
