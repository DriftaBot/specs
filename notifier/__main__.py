"""
Entrypoint: python -m notifier [discover|notify]

  discover  — find new consumer repos (>=100 stars) not yet in consumer.companies.yaml,
              check them against provider specs, register + raise issues if drift found.
  notify    — check all repos already in consumer.companies.yaml against provider specs
              and raise issues where drift is found.

With ANTHROPIC_API_KEY set: runs the LangGraph ReAct agent for the chosen mode.
Without ANTHROPIC_API_KEY: runs the deterministic runner for the chosen mode.
"""
import os
import sys


_USAGE = "Usage: python -m notifier [discover|notify]"

_DISCOVER_PROMPT = (
    "Discover new GitHub repositories that consume company APIs but are not yet "
    "registered in consumer.companies.yaml. "
    "For each company, call search_consumer_repos to find candidates with >=100 stars "
    "that are not already registered. "
    "For each new candidate, call check_consumer_repo. "
    "If issues are found, register the repo and raise a GitHub issue. "
    "Process all companies. Print a summary at the end."
)

_NOTIFY_PROMPT = (
    "Check all consumer repositories already registered in consumer.companies.yaml "
    "against the current provider specs in companies/providers/. "
    "For each registered consumer, call check_consumer_repo and raise a GitHub issue "
    "if incorrect or outdated API usage is found. "
    "Process all registered consumers. Print a summary at the end."
)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    if mode not in ("discover", "notify"):
        print(_USAGE)
        sys.exit(1)

    if os.environ.get("ANTHROPIC_API_KEY"):
        print(f"ANTHROPIC_API_KEY detected — running LangGraph agent ({mode}).")
        from notifier.agent import build_agent
        prompt = _DISCOVER_PROMPT if mode == "discover" else _NOTIFY_PROMPT
        agent = build_agent()
        final_state = agent.invoke({"messages": [("user", prompt)]})
        for msg in reversed(final_state["messages"]):
            if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                print("\n" + "=" * 60)
                print(msg.content)
                print("=" * 60)
                break
    else:
        print(f"No ANTHROPIC_API_KEY — running deterministic runner ({mode}).")
        from notifier.runner import run_discover, run_notify
        if mode == "discover":
            run_discover()
        else:
            run_notify()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\nNotifier interrupted.")
        sys.exit(1)
