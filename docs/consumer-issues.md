# Consumer Issues

When DriftaBot checks a consumer repo and detects incorrect or outdated API usage, it opens a GitHub issue via the [@driftabot-agent](https://github.com/driftabot-agent) account.

## Issue format

**Title:**
```
[DriftaBot] Breaking change in Stripe API: `<deprecated-field-or-removed-endpoint>`
```

**Body:**

```markdown
## Breaking API Change — Stripe API

**DriftaBot** detected breaking changes in the **Stripe** API that may affect this repository.

### Deprecated fields

**Resource `charges`** — deprecated fields:
- `card`

### Affected files
- `src/billing/client.py`
- `tests/test_payments.py`

### Next steps
1. Review the files listed above and update any references to the changed endpoints or fields.
2. Check the Stripe API changelog for migration guidance.

---
*Opened by [DriftaBot](https://github.com/DriftaBot/registry)*
```

## Deduplication

Before opening an issue, DriftaBot checks for existing open issues with the same title created by `@driftabot-agent`. If a duplicate is found, no new issue is created.

## Issue logs

Every issue created or detected as a duplicate is logged locally to:

```
companies/consumers/<owner>/<repo>/issues/<number>.json
```

```json
{
  "url": "https://github.com/owner/repo/issues/42",
  "title": "[DriftaBot] Breaking change in Stripe API: `card`",
  "company": "Stripe",
  "status": "created",
  "created_at": "2026-03-15T12:55:17Z"
}
```

## False positives

Claude's semantic analysis is generally accurate, but can occasionally flag a repo that doesn't directly call the affected endpoint. If you receive a false positive, close the issue — DriftaBot will not reopen it for the same change.

To avoid false positives entirely, [register your repo](consumers) in `consumer.companies.yaml`.
