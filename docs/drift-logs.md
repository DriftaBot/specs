# Drift Logs

Every time the notifier runs and detects changes in a spec, it writes a drift result file to:

```
companies/providers/<company>/drift/result_<spec_type>_<YYYYMMDD_HHMMSS>.json
```

Example: `companies/providers/stripe/drift/result_openapi_20260315_040000.json`

Files sort newest-first when listed with `ls -r`.

## File format

```json
{
  "detected_at": "2026-03-15T04:00:00",
  "company": "stripe",
  "spec_type": "openapi",
  "spec_path": "companies/providers/stripe/openapi/stripe.openapi.json",
  "summary": {
    "breaking": 2,
    "non_breaking": 1,
    "info": 0
  },
  "changes": [
    {
      "type": "field_removed",
      "severity": "breaking",
      "path": "/v1/customers/{customer}",
      "method": "GET",
      "location": "response.body.email",
      "description": "Response field 'email' removed from GET /v1/customers/{customer}"
    },
    {
      "type": "field_added",
      "severity": "non_breaking",
      "path": "/v1/customers",
      "method": "POST",
      "location": "request.body.metadata",
      "description": "New optional field 'metadata' added"
    }
  ]
}
```

## Fields

| Field | Description |
|-------|-------------|
| `detected_at` | ISO 8601 local timestamp when the diff was run |
| `company` | Company slug from `provider.companies.yaml` |
| `spec_type` | `openapi`, `graphql`, or `grpc` |
| `spec_path` | Path to the spec file relative to the repo root |
| `summary.breaking` | Count of breaking changes |
| `summary.non_breaking` | Count of non-breaking changes |
| `summary.info` | Count of informational changes |
| `changes` | All changes, sorted breaking → non_breaking → info |

## Change severities

Severity classification is performed by the [driftabot/engine](https://driftabot.github.io/engine/severity-rules) CLI. Consumer notifications are only triggered for `breaking` changes.

| Severity | Examples |
|----------|---------|
| `breaking` | Removed field, renamed required parameter, changed response type |
| `non_breaking` | New optional field, new endpoint, expanded enum |
| `info` | Deprecation notice, description change |
