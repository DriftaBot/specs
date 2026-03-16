# DriftaBot Registry

The central, always-up-to-date repository for public API specifications from major companies. Consumer repositories are checked against current provider specs and notified via GitHub issues when their API usage is incorrect or outdated.

**[Full documentation](https://driftabot.github.io/registry/)**

## Automated Workflows

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| `crawl-providers` | Daily 00:00 UTC | Fetches fresh provider specs, runs the `@driftabot/engine` diff, saves drift results to `drifts/<org>/<repo>/result.json` |
| `discover-providers` | Manual dispatch | Discovers new public API providers not yet in `provider.companies.yaml` |
| `discover-consumers` | Weekly Monday 02:00 UTC | Finds new consumer repos (≥100 stars) not in `consumer.companies.yaml`, checks them, registers + writes pass/fail results |
| `scan-consumers` | Weekly Wednesday 04:00 UTC | Scans all registered consumers in `consumer.companies.yaml` against provider specs, writes results to `companies/consumers/pass\|fail` |
| `docs` | On push to `main` | Rebuilds GitHub Pages |

## Secrets Required

| Secret | Used by | Description |
|--------|---------|-------------|
| `GITHUB_TOKEN` | All workflows | Auto-provided by GitHub Actions. Read specs, commit updates, Code Search. |
| `ANTHROPIC_API_KEY` | Crawler, Notifier | Powers the LangGraph agent (Claude). |
| `DRIFTABOT_TOKEN` | Notifier | PAT for the [@driftabot-agent](https://github.com/driftabot-agent) account (`public_repo` scope). Creates issues in consumer repos. |

## GitHub Policy Compliance

- All specs are fetched from **public** GitHub repositories only.
- The GitHub REST API is used (no HTML scraping), respecting GitHub's [Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies).
- Authenticated requests stay well within the 5,000 req/hr rate limit.
- This project is open source and non-commercial.
