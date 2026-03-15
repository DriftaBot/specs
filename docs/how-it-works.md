# How It Works

DriftaBot Specs has two automated pipelines: a **crawler** that keeps specs up to date, and a **notifier** that alerts consumer repos when breaking changes are detected.

## Crawler (every 6 hours)

```
provider.companies.yaml  →  crawl-specs workflow  →  companies/providers/
```

1. [`provider.companies.yaml`](https://github.com/DriftaBot/specs/blob/main/provider.companies.yaml) maps each company to the GitHub repo and file path(s) where their spec lives.
2. The [`crawl-specs`](https://github.com/DriftaBot/specs/blob/main/.github/workflows/crawl-specs.yml) workflow runs on a schedule every 6 hours.
3. **Cost optimisation** — at midnight UTC the workflow uses a LangGraph ReAct agent powered by Claude. The other three daily runs use a fast deterministic crawler with no LLM cost.
4. Each spec is fetched, SHA-256 hashed, and compared with the stored version. Changed specs are written and committed.

## Notifier (on spec update)

```
companies/providers/ commit  →  notify-consumers workflow  →  GitHub issues
```

1. Every push that changes files under `companies/providers/` (excluding `drift/`) triggers the [`notify-consumers`](https://github.com/DriftaBot/specs/blob/main/.github/workflows/notify-consumers.yml) workflow.
2. The [driftabot/engine](https://driftabot.github.io/engine) CLI diffs the new spec against the previous commit.
3. Drift results are written to `companies/providers/<company>/drift/` for every run.
4. GitHub Code Search finds public repos that import the affected company's client libraries (capped at 20 per company).
5. Repos in [`consumer.companies.yaml`](https://github.com/DriftaBot/specs/blob/main/consumer.companies.yaml) are always included regardless of the cap.
6. For each candidate repo, a second Code Search query checks whether the repo actually references the broken endpoint.
7. A GitHub issue is opened in each affected repo by [@driftabot-agent](https://github.com/driftabot-agent).

## Notifier modes

The notifier runs in one of two modes depending on whether `ANTHROPIC_API_KEY` is available:

| Mode | When | How |
|------|------|-----|
| **LangGraph agent** | `ANTHROPIC_API_KEY` set | Claude ReAct agent orchestrates all five phases via tools |
| **Deterministic** | no `ANTHROPIC_API_KEY` | Plain Python runner — same logic, no LLM, no API cost |

In GitHub Actions, `ANTHROPIC_API_KEY` is always passed so the agent runs. Locally, `make notify` uses the deterministic path and `make notify-agent` uses the LangGraph agent.

## Spec directory layout

```
companies/
└── providers/
    ├── stripe/
    │   ├── openapi/                          spec files
    │   └── drift/                            breaking change logs
    │       └── result_openapi_20260315_040000.json
    ├── twilio/openapi/
    ├── github/openapi/
    ├── slack/openapi/
    ├── sendgrid/openapi/
    ├── digitalocean/openapi/
    ├── netlify/openapi/
    ├── pagerduty/openapi/
    ├── shopify/graphql/
    └── google/grpc/
```
