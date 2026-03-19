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
ANTHROPIC_API_KEY=   # only needed for agent mode
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

## Tokens

| Token | How to get | Required for |
|-------|-----------|-------------|
| `GITHUB_TOKEN` | `gh auth token` | All commands |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | `make crawl-agent` |

## GitHub Actions workflows

| Workflow | Schedule | Description |
|----------|----------|-------------|
| `crawl-providers.yml` | Daily 00:00 UTC | Fetches and commits updated provider specs; runs `@driftabot/engine` diff |
| `discover-providers.yml` | Manual dispatch | Discovers new API providers, updates `provider.companies.yaml` |
| `docs.yml` | On push to `main` | Builds and deploys VitePress docs to GitHub Pages |
