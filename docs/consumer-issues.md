# Consumer Issues

When a breaking change is detected and a consumer repo is found to reference the affected endpoint, DriftaBot opens a GitHub issue via the [@driftabot-agent](https://github.com/driftabot-agent) account.

## Issue format

**Title:**
```
[DriftaBot] Breaking change in Stripe API: <description>
```

**Body:**

```markdown
## Breaking API Change — Stripe API

**DriftaBot** detected a breaking change in the **Stripe** API that may affect this repository.

### What changed
**<description>**

| | |
|---|---|
| **Type** | `field_removed` |
| **Path** | `/v1/customers/{id}` `GET` |
| **Location** | `response.body.email` |
| **Severity** | Breaking |

**Spec:** [companies/providers/stripe/openapi/stripe.openapi.json](https://github.com/DriftaBot/specs/blob/<sha>/companies/providers/stripe/openapi/stripe.openapi.json)

### Files referencing this endpoint
- `src/billing/client.py`
- `tests/test_payments.py`

### Next steps
1. Review the files listed above and update any references to the changed endpoint or field.
2. Check the Stripe API changelog for migration guidance.

---
*Created by [DriftaBot](https://github.com/DriftaBot/specs) · If this is a false positive, close the issue.*
```

## Labels

Issues are created with the label `api-breaking-change`.

## Deduplication

Before opening an issue, DriftaBot checks for existing open issues with the same title created by `@driftabot-agent`. If a duplicate is found, no new issue is created.

## False positives

Code Search-based discovery can occasionally match repos that don't directly call the affected endpoint. If you receive a false positive, close the issue — DriftaBot will not reopen it for the same change.

To avoid false positives entirely, [register your repo](consumers) in `consumer.companies.yaml`. Registered repos skip Code Search and always receive targeted notifications.
