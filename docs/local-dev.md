# Local Development

## Prerequisites

- Python 3.12+
- A GitHub token with public repo read access

## Setup

```bash
# Clone the repo
git clone https://github.com/DriftaBot/registry.git
cd registry

# Install Python dependencies
pip install -e .

# Copy and fill in your tokens
cp .env.example .env
```

**.env:**
```bash
GITHUB_TOKEN=        # gh auth token
ANTHROPIC_API_KEY=   # only needed for agent modes
DRIFTABOT_TOKEN=     # only needed for make notify / notify-agent
```

All `make` commands load `.env` automatically.

## Make commands

### Crawler

```bash
make crawl          # deterministic crawler — no LLM, no API cost
make crawl-agent    # LangGraph agent crawler — requires ANTHROPIC_API_KEY
```

### Notifier

```bash
make notify         # deterministic notifier — no LLM, no API cost
make notify-agent   # LangGraph agent notifier — requires ANTHROPIC_API_KEY
```

### Consumer checker

```bash
make check-consumer REPO=spree/spree_stripe COMPANY=stripe
```

See [Check Your Repo](check-consumer) for full documentation.

## Tokens

| Token | How to get | Required for |
|-------|-----------|-------------|
| `GITHUB_TOKEN` | `gh auth token` | All commands |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | `make crawl-agent`, `make notify-agent` |
| `DRIFTABOT_TOKEN` | PAT for [@driftabot-agent](https://github.com/driftabot-agent) (`public_repo` scope) | `make notify`, `make notify-agent` |

## GitHub Actions workflows

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `crawl-specs.yml` | Every 6 hours + `workflow_dispatch` | Fetches and commits updated provider specs |
| `notify-consumers.yml` | `workflow_dispatch` | Checks consumer repos against current specs, opens issues if needed |
