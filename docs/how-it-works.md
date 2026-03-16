# How It Works

DriftaBot Registry runs five automated GitHub Actions workflows that keep provider specs current, discover and check consumer repos, and rebuild documentation.

## Workflow pipeline

```
provider.companies.yaml
        │
        ▼
crawl-providers (daily 00:00 UTC)
  python -m crawler
  @driftabot/engine diff
        │
        ├─► companies/providers/   (updated specs)
        └─► drifts/                (per-repo drift results)

discover-providers (manual dispatch)
  python -m discoverer
        │
        └─► provider.companies.yaml  (new entries)

discover-consumers (weekly Monday 02:00 UTC)
  python -m notifier discover
        │
        ├─► consumer.companies.yaml  (newly registered repos)
        └─► companies/consumers/pass|fail/

scan-consumers (weekly Wednesday 04:00 UTC)
  python -m notifier scan
        │
        └─► companies/consumers/pass|fail/
```

## 1. crawl-providers (daily 00:00 UTC)

1. [`provider.companies.yaml`](https://github.com/DriftaBot/registry/blob/main/provider.companies.yaml) maps each company to the GitHub repo and file path(s) where their spec lives.
2. `python -m crawler` fetches each spec and commits any changes to `companies/providers/`.
3. `scripts/run_diff.py` runs the `@driftabot/engine` NPM package to diff changed specs and writes results to `drifts/<org>/<repo>/result.json`.
4. **Cost optimisation** — with `ANTHROPIC_API_KEY` set, the crawler runs as a LangGraph ReAct agent (Claude). Without it, a fast deterministic runner is used instead with no LLM cost.

## 2. discover-providers (manual dispatch)

`python -m discoverer` searches GitHub for public API providers not yet in `provider.companies.yaml` and adds new entries. Results are committed back to the repo. Triggered manually via `workflow_dispatch`.

## 3. discover-consumers (weekly Monday 02:00 UTC)

`python -m notifier discover` finds new public repos (≥100 stars) that import a tracked provider's client libraries but are not yet in `consumer.companies.yaml`. Each candidate is checked against the current provider spec. If issues are found, the repo is registered and a GitHub issue is opened by [@driftabot-agent](https://github.com/driftabot-agent). Pass/fail results are written to `companies/consumers/`.

## 4. scan-consumers (weekly Wednesday 04:00 UTC)

`python -m notifier scan` checks every repo already registered in `consumer.companies.yaml` against the current provider specs in `companies/providers/`. Results are written to `companies/consumers/pass|fail`. Issues are opened for any new problems found.

## 5. docs (on push to main)

Rebuilds and deploys the VitePress documentation site to GitHub Pages whenever `docs/`, `companies/`, or `provider.companies.yaml` changes on `main`, or when a semver tag is pushed.

## Notifier modes

Both `discover` and `scan` run in one of two modes depending on whether `ANTHROPIC_API_KEY` is available:

| Mode | When | How |
|------|------|-----|
| **LangGraph agent** | `ANTHROPIC_API_KEY` set | Claude ReAct agent orchestrates discovery and checking via tools |
| **Deterministic** | no `ANTHROPIC_API_KEY` | Plain Python runner — same logic, no LLM, no API cost |

In GitHub Actions, `ANTHROPIC_API_KEY` is always passed so the agent runs. Locally, omitting the key uses the deterministic path.

## Directory layout

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
    ├── pass/<owner>/<repo>/     scan pass results
    └── fail/<owner>/<repo>/     scan fail results + issue logs
drifts/
└── <org>/<repo>/result.json    spec diff output from @driftabot/engine
```
