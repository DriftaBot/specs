# How It Works

DriftaBot Registry runs three automated GitHub Actions workflows that keep provider specs current and rebuild documentation.

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
```

## 1. crawl-providers (daily 00:00 UTC)

1. [`provider.companies.yaml`](https://github.com/DriftaBot/registry/blob/main/provider.companies.yaml) maps each company to the GitHub repo and file path(s) where their spec lives.
2. `python -m crawler` fetches each spec and commits any changes to `companies/providers/`.
3. `scripts/run_diff.py` runs the `@driftabot/engine` NPM package to diff changed specs and writes results to `drifts/<org>/<repo>/result.md`.
4. **Cost optimisation** — with `ANTHROPIC_API_KEY` set, the crawler runs as a LangGraph ReAct agent (Claude). Without it, a fast deterministic runner is used instead with no LLM cost.

## 2. discover-providers (manual dispatch)

`python -m discoverer` searches GitHub for public API providers not yet in `provider.companies.yaml` and adds new entries. Results are committed back to the repo. Triggered manually via `workflow_dispatch`.

## 3. docs (on push to main)

Rebuilds and deploys the VitePress documentation site to GitHub Pages whenever `docs/`, `companies/`, or `provider.companies.yaml` changes on `main`, or when a semver tag is pushed.

## Crawler modes

The crawler runs in one of two modes depending on whether `ANTHROPIC_API_KEY` is available:

| Mode | When | How |
|------|------|-----|
| **LangGraph agent** | `ANTHROPIC_API_KEY` set | Claude ReAct agent orchestrates spec fetching via tools |
| **Deterministic** | no `ANTHROPIC_API_KEY` | Plain Python runner — same logic, no LLM, no API cost |

In GitHub Actions, `ANTHROPIC_API_KEY` is always passed so the agent runs. Locally, omitting the key uses the deterministic path.

## OpenClaw integration

The [`openclaw/`](https://github.com/DriftaBot/registry/tree/main/openclaw) directory contains a ready-to-use [OpenClaw](https://docs.openclaw.ai/) skill and agent tool plugin. Once installed, any OpenClaw agent can answer questions about providers and breaking changes via natural language.

**Skill** (`openclaw/skills/driftabot/SKILL.md`) — prompt-level instructions, no build step.

**Plugin** (`openclaw/plugins/driftabot-tool/`) — three structured tools:

| Tool | Description |
|------|-------------|
| `driftabot_list_providers` | Lists all tracked providers with spec types and repos |
| `driftabot_get_drift` | Returns the latest drift/breaking-change report for a provider |
| `driftabot_get_spec_info` | Returns spec type, GitHub repo, and path for a provider |

All tools fetch directly from `raw.githubusercontent.com/DriftaBot/registry/main` — no API key required.

## Directory layout

```
companies/
└── providers/
    ├── stripe/openapi/          current spec files
    ├── twilio/openapi/
    ├── github/openapi/
    ├── slack/openapi/
    ├── sendgrid/openapi/
    ├── digitalocean/openapi/
    ├── netlify/openapi/
    ├── pagerduty/openapi/
    ├── shopify/graphql/
    └── google/grpc/
drifts/
└── <org>/<repo>/result.md      spec diff output from @driftabot/engine
openclaw/
├── skills/driftabot/           OpenClaw skill (SKILL.md)
└── plugins/driftabot-tool/     OpenClaw agent tool plugin (TypeScript)
```
