# Local Development

## Prerequisites

- Python 3.12+
- [driftabot/engine](https://driftabot.github.io/engine/install) CLI binary
- A GitHub token with public repo read access

## Setup

```bash
# Clone the repo
git clone https://github.com/DriftaBot/specs.git
cd specs

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

## Running against a real spec change

To test the full notifier pipeline locally:

```bash
# 1. Make a small edit to a spec file
echo "" >> companies/providers/stripe/openapi/stripe.openapi.json

# 2. Commit it (the notifier reads HEAD~1 for the diff)
git add . && git commit -m "test: trigger notifier"

# 3. Run the notifier (dry-run: no issues created without DRIFTABOT_TOKEN)
make notify

# 4. Revert
git reset --hard HEAD~1
```

## GitHub Actions workflows

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `crawl-specs.yml` | Every 6 hours + `workflow_dispatch` | Fetches and commits updated specs |
| `notify-consumers.yml` | Push to `companies/providers/**` (excl. `drift/`) | Detects breaking changes, notifies consumers |
