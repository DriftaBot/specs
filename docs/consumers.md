# Register for Notifications

There are two ways a repo can receive breaking change notifications from DriftaBot.

## Dynamic discovery (automatic)

The `discover-consumers` workflow runs weekly on Mondays at 02:00 UTC. It uses GitHub Code Search to find public repos (≥100 stars) that reference a provider's client libraries and are not yet registered. Each candidate is checked against the current provider spec.

If issues are found, the repo is registered in `consumer.companies.yaml` automatically, a GitHub issue is opened, and the repo will be included in every future `scan-consumers` run.

The trade-off: dynamic discovery relies on Code Search matching your import patterns. Registering explicitly (below) guarantees you are always checked.

## Opt-in registry (recommended)

Register your repo in [`consumer.companies.yaml`](https://github.com/DriftaBot/registry/blob/main/consumer.companies.yaml) to be checked by the `scan-consumers` workflow (weekly Wednesday 04:00 UTC):

- **Always checked** — registered repos are never skipped
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
| [ansible-collections/community.general](https://github.com/ansible-collections/community.general) | sendgrid |
| [auth0/rules](https://github.com/auth0/rules) | sendgrid |
| [kaansoral/adventureland](https://github.com/kaansoral/adventureland) | stripe |
