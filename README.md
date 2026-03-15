# DriftaBot Specs

The central, always-up-to-date repository for public API specifications from major companies.

Specs are automatically fetched every 6 hours from their canonical public GitHub repositories by a [LangGraph](https://github.com/langchain-ai/langgraph)-powered crawler agent running in GitHub Actions. When breaking changes are detected, affected consumer repositories are automatically notified via GitHub issues.

## Spec Directory

```
companies/
└── providers/
    ├── stripe/
    │   ├── openapi/        OpenAPI 3.0
    │   └── drift/          Breaking change logs (auto-generated)
    ├── twilio/openapi/     OpenAPI 3.0 (all service specs)
    ├── github/openapi/     OpenAPI 3.0/3.1
    ├── slack/openapi/      OpenAPI 2.0
    ├── sendgrid/openapi/   OpenAPI 3.0
    ├── digitalocean/openapi/ OpenAPI 3.0
    ├── netlify/openapi/    OpenAPI 2.0
    ├── pagerduty/openapi/  OpenAPI 3.0
    ├── shopify/graphql/    GraphQL SDL
    └── google/grpc/        gRPC / Protobuf
```

## File Naming

```
companies/providers/<company>/<spec_type>/<filename>.<spec_type>.<ext>
companies/providers/<company>/drift/result_<spec_type>_<YYYYMMDD_HHMMSS>.json
```

Examples:
- `companies/providers/stripe/openapi/stripe.openapi.json`
- `companies/providers/stripe/drift/result_openapi_20260315_040000.json`
- `companies/providers/shopify/graphql/shopify_admin.graphql`
- `companies/providers/google/grpc/pubsub_v1/pubsub.proto`

## How It Works

### Crawler (every 6 hours)

1. [provider.companies.yaml](provider.companies.yaml) is the registry — it maps each company to the GitHub repo and file path(s) where their specs live.
2. A GitHub Actions [scheduled workflow](.github/workflows/crawl-specs.yml) runs every 6 hours.
3. At midnight UTC the workflow uses a LangGraph ReAct agent (Claude-powered). The other three runs use a fast deterministic crawler to save API costs.
4. The crawler fetches each spec, compares it with the stored version, and writes any updates.
5. Updated specs are committed and pushed back to this repo automatically.

### Consumer Notifier (on spec update)

1. After every commit that updates files under `companies/providers/` (excluding `drift/`), the [notify-consumers workflow](.github/workflows/notify-consumers.yml) triggers automatically.
2. The [driftabot/engine](https://github.com/DriftaBot/engine) CLI compares old vs new specs to detect breaking changes.
3. Drift results are written to `companies/providers/<company>/drift/` — one JSON file per run, sorted newest-first by filename.
4. GitHub Code Search finds public repositories that import the affected company's client libraries.
5. Repos registered in [consumer.companies.yaml](consumer.companies.yaml) are always notified (opt-in, no cap).
6. A GitHub issue is opened in each affected repo by the [@driftabot-agent](https://github.com/driftabot-agent) account.

The notifier runs in one of two modes depending on whether `ANTHROPIC_API_KEY` is set:

| Mode | Trigger | How |
|------|---------|-----|
| **LangGraph agent** | `ANTHROPIC_API_KEY` is set | Claude ReAct agent orchestrates the workflow via tools |
| **Deterministic** | no `ANTHROPIC_API_KEY` | Plain Python runner — same logic, no LLM, no API cost |

In CI, `ANTHROPIC_API_KEY` is always passed so the agent runs. Locally, `make notify` uses the deterministic path; `make notify-agent` uses the LangGraph agent.

### Drift Result Format

```json
{
  "detected_at": "2026-03-15T04:00:00",
  "company": "stripe",
  "spec_type": "openapi",
  "spec_path": "companies/providers/stripe/openapi/stripe.openapi.json",
  "summary": { "breaking": 2, "non_breaking": 1, "info": 0 },
  "changes": [
    { "severity": "breaking", "type": "field_removed", "path": "/v1/customers", ... },
    ...
  ]
}
```

Changes are sorted breaking → non_breaking → info. List newest results first with `ls -r companies/providers/<company>/drift/`.

## Adding a New API Provider

1. Find the company's public GitHub repo with their API spec.
2. Add an entry to [provider.companies.yaml](provider.companies.yaml):

```yaml
- name: acme
  display_name: Acme Corp
  specs:
    - type: openapi
      repo: acme/openapi
      path: spec/openapi.json
      output: companies/providers/acme/openapi/acme.openapi.json
  consumers:
    - query: "acme-sdk language:python"
    - query: "require(\"acme\") language:javascript"
```

3. Open a pull request — the next crawler run will pick it up automatically.

## Register Your Repo for Notifications

To receive breaking change notifications for any provider, open a PR adding your repo to [consumer.companies.yaml](consumer.companies.yaml):

```yaml
consumers:
  - repo: your-org/your-repo
    companies:
      - stripe
      - twilio
    contact: team@your-org.com   # optional
```

Registered repos are always notified — they bypass the dynamic search cap and are never false-positived out.

## Running Locally

Copy `.env.example` to `.env` and fill in your tokens. All `make` commands load `.env` automatically.

```bash
# Install dependencies
pip install -e .

# Run the crawler (deterministic, no LLM cost)
make crawl

# Run the crawler with the LangGraph agent (requires ANTHROPIC_API_KEY)
make crawl-agent

# Run the consumer notifier
make notify

# Run the notifier with the LangGraph agent
make notify-agent

# Check if a repo uses deprecated or removed API endpoints
make check-consumer REPO=spree/spree_stripe COMPANY=stripe
```

### Generating a GITHUB_TOKEN

```bash
# Fastest — reuse your existing gh CLI session:
gh auth token
```

Or create a fine-grained PAT at **GitHub → Settings → Developer settings → Personal access tokens** with `Contents: Read` on public repositories.

## GitHub Policy Compliance

- All specs are fetched from **public** GitHub repositories only.
- The GitHub REST API is used (no HTML scraping), respecting GitHub's [Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies).
- Authenticated requests stay well within the 5,000 req/hr rate limit.
- This project is open source and non-commercial.

## Secrets Required

| Secret | Used by | Description |
|--------|---------|-------------|
| `GITHUB_TOKEN` | Crawler, Notifier | Auto-provided by GitHub Actions. Read specs, commit updates, Code Search. |
| `ANTHROPIC_API_KEY` | Crawler, Notifier | Powers the LangGraph agent (Claude). Crawler uses it once per day at midnight UTC. |
| `DRIFTABOT_TOKEN` | Notifier | PAT for the [@driftabot-agent](https://github.com/driftabot-agent) account (`public_repo` scope). Creates issues in consumer repos. |
