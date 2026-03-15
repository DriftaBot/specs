# DriftaBot Registry

The central, always-up-to-date repository for public API specifications from major companies.

API specs are automatically fetched and stored in `companies/providers/`. Consumer repositories are checked against the current spec and notified via GitHub issues when their API usage is incorrect or outdated.

**[→ Full documentation](https://driftabot.github.io/registry/)**

## Spec Directory

```
companies/
└── providers/
    ├── stripe/openapi/       OpenAPI 3.0
    ├── twilio/openapi/       OpenAPI 3.0 (all service specs)
    ├── github/openapi/       OpenAPI 3.0/3.1
    ├── slack/openapi/        OpenAPI 2.0
    ├── sendgrid/openapi/     OpenAPI 3.0
    ├── digitalocean/openapi/ OpenAPI 3.0
    ├── netlify/openapi/      OpenAPI 2.0
    ├── pagerduty/openapi/    OpenAPI 3.0
    ├── shopify/graphql/      GraphQL SDL
    └── google/grpc/          gRPC / Protobuf
```

## Quick Start

| Task | Link |
|------|------|
| Add an API provider | [docs/providers](https://driftabot.github.io/registry/providers) |
| Register for notifications | [docs/consumers](https://driftabot.github.io/registry/consumers) |
| Check a repo for API issues | [docs/check-consumer](https://driftabot.github.io/registry/check-consumer) |
| Run locally | [docs/local-dev](https://driftabot.github.io/registry/local-dev) |

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
