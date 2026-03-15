# Check Your Repo

`make check-consumer` scans a GitHub repository against a provider's local OpenAPI spec and reports which endpoints are in use and whether any reference deprecated or removed fields.

## Usage

```bash
make check-consumer REPO=owner/repo COMPANY=stripe
```

`GITHUB_TOKEN` must be set (in `.env` or your shell). Only public repo read access is required.

```bash
# Fastest — reuse your existing gh CLI session:
export GITHUB_TOKEN=$(gh auth token)

make check-consumer REPO=spree/spree_stripe COMPANY=stripe
```

## Example output

```
Checking  : spree/spree_stripe
Against   : Stripe OpenAPI spec (companies/providers/stripe/openapi/stripe.openapi.json)
Resources : 94 endpoint groups in spec

Used  : 7 resource(s)
Unused: 87 resource(s)

  ✓ payment_intents  (16 file match(es))
      app/models/spree_stripe/gateway/payment_intents.rb
      app/services/spree_stripe/create_payment_intent.rb
  ✓ customers  (3 file match(es))
      app/services/spree_stripe/update_customer.rb
  ✓ payment_methods  (9 file match(es))
  ✓ webhook_endpoints  (2 file match(es))
  ✓ payment_method_domains  (2 file match(es))
  ✓ charges  (2 file match(es))
  ✓ refunds  (1 file match(es))

Result: OK — 7 resource(s) used, all current.
```

If deprecated fields are found:

```
  ⚠ charges  (2 file match(es))
      app/models/payment.rb
      DEPRECATED FIELDS:
        - POST /v1/charges -> source (use payment_method instead)

Result: 1 issue(s) found — deprecated fields in use.
```

The command exits with code `1` if issues are found, making it suitable for CI.

## How it works

1. Loads the local OpenAPI spec for the company from `companies/providers/<company>/openapi/`.
2. Extracts every resource group (second path segment, e.g. `payment_intents` from `/v1/payment_intents`).
3. For each resource, runs a GitHub Code Search query: `repo:<owner/repo> "<resource>"`.
4. Cross-references matches against the spec to flag deprecated fields.
5. Prints a report and exits 0 (clean) or 1 (issues found).

## Limitations

- Uses keyword matching on resource names — not SDK method calls. A match means the word appears somewhere in the file, not necessarily in an API call.
- Rate-limited to ~25 Code Search requests per minute. Large specs with many resource groups may take a few minutes.
- Only checks OpenAPI specs. GraphQL and gRPC support is not yet implemented.
