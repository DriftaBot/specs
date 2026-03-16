# Local Development

## Prerequisites

- Python 3.12+
- Node.js 20+ (for the `@driftabot/engine` diff step)
- A GitHub token with public repo read access

## Setup

```bash
# Clone the repo
git clone https://github.com/DriftaBot/registry.git
cd registry

# Install Python dependencies
pip install -e .

# Install the DriftaBot engine (used by crawl-providers)
npm install -g @driftabot/engine

# Copy and fill in your tokens
cp .env.example .env
```

**.env:**
```bash
GITHUB_TOKEN=        # gh auth token
ANTHROPIC_API_KEY=   # only needed for agent modes
DRIFTABOT_TOKEN=     # only needed for notifier commands
```

All `make` commands load `.env` automatically.

## Make commands

### Crawler

```bash
make crawl          # deterministic crawler — no LLM, no API cost
make crawl-agent    # LangGraph agent crawler — requires ANTHROPIC_API_KEY
```

### Provider discoverer

```bash
python -m discoverer   # discover new providers and update provider.companies.yaml
```

### Notifier

```bash
python -m notifier discover   # find new consumer repos, check and register them
python -m notifier scan       # scan all registered consumers in consumer.companies.yaml
```

With `ANTHROPIC_API_KEY` set, both commands run the LangGraph agent. Without it, the deterministic runner is used.

### Consumer checker

```bash
make check-consumer REPO=owner/repo COMPANY=stripe
# Check a repo and open a GitHub issue if problems are found:
make raise-issue    REPO=owner/repo COMPANY=stripe
# Check, open an issue, and register the repo in consumer.companies.yaml:
make add-consumer   REPO=owner/repo COMPANY=stripe
```

See [Check Your Repo](check-consumer) for full documentation.

## Tokens

| Token | How to get | Required for |
|-------|-----------|-------------|
| `GITHUB_TOKEN` | `gh auth token` | All commands |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | `make crawl-agent`, `python -m notifier` (agent mode) |
| `DRIFTABOT_TOKEN` | PAT for [@driftabot-agent](https://github.com/driftabot-agent) (`public_repo` scope) | `python -m notifier discover/scan`, `make raise-issue`, `make add-consumer` |

## GitHub Actions workflows

| Workflow | Schedule | Description |
|----------|----------|-------------|
| `crawl-providers.yml` | Daily 00:00 UTC | Fetches and commits updated provider specs; runs `@driftabot/engine` diff |
| `discover-providers.yml` | Manual dispatch | Discovers new API providers, updates `provider.companies.yaml` |
| `discover-consumers.yml` | Weekly Monday 02:00 UTC | Finds new consumer repos, checks and registers them |
| `scan-consumers.yml` | Weekly Wednesday 04:00 UTC | Scans all registered consumers, writes pass/fail results |
| `docs.yml` | On push to `main` | Builds and deploys VitePress docs to GitHub Pages |
