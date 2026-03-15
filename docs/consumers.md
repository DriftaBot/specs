# Register for Notifications

There are two ways a repo can receive breaking change notifications:

## Dynamic discovery (automatic)

GitHub Code Search automatically finds public repos that reference a provider's client libraries. Up to 20 repos per company are notified per run. No action required — if your repo imports a tracked SDK, it may already be discovered.

The trade-off: dynamic discovery is subject to the 20-repo cap and relies on Code Search matching your import patterns.

## Opt-in registry (recommended)

Register your repo in [`consumer.companies.yaml`](https://github.com/DriftaBot/specs/blob/main/consumer.companies.yaml) to receive notifications unconditionally:

- **No cap** — registered repos are always notified regardless of the 20-repo limit
- **No false negatives** — you won't be missed if Code Search doesn't match your import style
- **Pinned** — you stay registered even if your import patterns change

### How to register

Open a pull request adding your repo to `consumer.companies.yaml`:

```yaml
consumers:
  - repo: your-org/your-repo
    companies:
      - stripe
      - twilio
    contact: team@your-org.com   # optional
```

| Field | Required | Description |
|-------|----------|-------------|
| `repo` | ✓ | GitHub repo in `owner/repo` format |
| `companies` | ✓ | List of company names from `provider.companies.yaml` |
| `contact` | — | Optional email for internal tracking |

Company names must match the `name` field in `provider.companies.yaml` exactly (e.g. `stripe`, `twilio`, `github`, `slack`).

### Currently registered consumers

| Repo | Companies |
|------|-----------|
| [spree/spree_stripe](https://github.com/spree/spree_stripe) | stripe |
