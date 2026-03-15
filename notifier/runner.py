"""
Deterministic consumer notifier — no LLM required.

Discovers new consumer repos and checks all registered consumers against the
current provider specs in companies/providers/. Used as the fallback when
ANTHROPIC_API_KEY is not set.
"""
from checker.__main__ import check as check_repo
from crawler.config import load_consumer_registry, load_registry, register_consumer
from notifier.tools import (
    search_consumer_repos_plain,
)


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

    # Phase 1: check all registered consumers against current provider specs
    consumer_registry = load_consumer_registry()
    if not consumer_registry.consumers:
        print("No registered consumers. Done.")
        return

    print(f"\nChecking {len(consumer_registry.consumers)} registered consumer(s) against current provider specs...")
    for entry in consumer_registry.consumers:
        for company in entry.companies:
            print(f"  {entry.repo} → {company}")
            check_repo(entry.repo, company, raise_issue=True)
