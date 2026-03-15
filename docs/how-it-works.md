# How It Works

DriftaBot Registry has two automated pipelines: a **crawler** that keeps specs up to date, and a **notifier** that checks consumer repos against the current spec and raises issues when API usage is incorrect or outdated.

## Crawler (every 6 hours)

```
provider.companies.yaml  →  crawl-specs workflow  →  companies/providers/
```

1. [`provider.companies.yaml`](https://github.com/DriftaBot/registry/blob/main/provider.companies.yaml) maps each company to the GitHub repo and file path(s) where their spec lives.
2. The [`crawl-specs`](https://github.com/DriftaBot/registry/blob/main/.github/workflows/crawl-specs.yml) workflow runs on a schedule every 6 hours.
3. **Cost optimisation** — at midnight UTC the workflow uses a LangGraph ReAct agent powered by Claude. The other three daily runs use a fast deterministic crawler with no LLM cost.
4. Each spec is fetched, SHA-256 hashed, and compared with the stored version. Changed specs are written and committed to `companies/providers/`.

## Notifier (on demand)

```
consumer.companies.yaml + companies/providers/  →  notify-consumers workflow  →  GitHub issues
```

The notifier is triggered manually via `workflow_dispatch`. On each run:

1. **Discover new consumers** — GitHub Code Search finds public repos that import a provider's client libraries. Up to 20 new repos per run (across all companies) are checked. Repos already in [`consumer.companies.yaml`](https://github.com/DriftaBot/registry/blob/main/consumer.companies.yaml) are skipped.
2. **Check registered consumers** — every repo in `consumer.companies.yaml` is checked against the current provider spec in `companies/providers/`.
3. For each repo, the checker loads the current OpenAPI spec, searches the repo for API usage, and uses Claude to semantically determine whether any deprecated fields or removed endpoints are being called.
4. If issues are found, a GitHub issue is opened by [@driftabot-agent](https://github.com/driftabot-agent). A newly discovered repo is registered in `consumer.companies.yaml` only if issues are found.
5. The run stops after checking 20 repos total.

Provider specs in `companies/providers/` are always the source of truth — no spec diffing or change tracking is needed.

## Notifier modes

The notifier runs in one of two modes depending on whether `ANTHROPIC_API_KEY` is available:

| Mode | When | How |
|------|------|-----|
| **LangGraph agent** | `ANTHROPIC_API_KEY` set | Claude ReAct agent orchestrates discovery and checking via tools |
| **Deterministic** | no `ANTHROPIC_API_KEY` | Plain Python runner — same logic, no LLM, no API cost |

In GitHub Actions, `ANTHROPIC_API_KEY` is always passed so the agent runs. Locally, `make notify` uses the deterministic path and `make notify-agent` uses the LangGraph agent.

## Spec directory layout

```
companies/
├── providers/
│   ├── stripe/openapi/          current spec files
│   ├── twilio/openapi/
│   ├── github/openapi/
│   ├── slack/openapi/
│   ├── sendgrid/openapi/
│   ├── digitalocean/openapi/
│   ├── netlify/openapi/
│   ├── pagerduty/openapi/
│   ├── shopify/graphql/
│   └── google/grpc/
└── consumers/
    └── <owner>/<repo>/issues/   issue logs written by the notifier
```
