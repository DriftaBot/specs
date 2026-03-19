<img src="docs/public/logo.png" alt="DriftaBot" width="120">

# DriftaBot Registry

The central, always-up-to-date repository for public API specifications from major companies.

**[Full documentation](https://driftabot.github.io/registry/)**

## Automated Workflows

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| `crawl-providers` | Daily 00:00 UTC | Fetches fresh provider specs, runs the `@driftabot/engine` diff, saves drift results to `drifts/<org>/<repo>/result.json` |
| `discover-providers` | Manual dispatch | Discovers new public API providers not yet in `provider.companies.yaml` |
| `docs` | On push to `main` | Rebuilds GitHub Pages |

## Secrets Required

| Secret | Used by | Description |
|--------|---------|-------------|
| `GITHUB_TOKEN` | All workflows | Auto-provided by GitHub Actions. Read specs, commit updates. |
| `ANTHROPIC_API_KEY` | Crawler | Powers the LangGraph agent (Claude). |

## GitHub Policy Compliance

- All specs are fetched from **public** GitHub repositories only.
- The GitHub REST API is used (no HTML scraping), respecting GitHub's [Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies).
- Authenticated requests stay well within the 5,000 req/hr rate limit.
- This project is open source and non-commercial.
