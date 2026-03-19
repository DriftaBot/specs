# Add a Provider

Anyone can add a new API provider by opening a pull request. The crawler will pick it up automatically on its next run.

## Steps

**1. Find the provider's public GitHub repo** that contains their API spec (OpenAPI, GraphQL, or gRPC).

**2. Add an entry to [`provider.companies.yaml`](https://github.com/DriftaBot/registry/blob/main/provider.companies.yaml):**

```yaml
- name: acme                          # unique slug (lowercase, no spaces)
  display_name: Acme Corp             # human-readable name
  specs:
    - type: openapi                   # openapi | graphql | grpc
      repo: acme/openapi-spec         # GitHub repo containing the spec
      path: spec/openapi.json         # path to the spec file within that repo
      output: companies/providers/acme/openapi/acme.openapi.json
```

**3. Open a pull request.** The next crawler run will fetch the spec and commit it.

## Multiple spec files

For providers with many spec files (e.g. Twilio), use `path_pattern` and `output_dir` instead of `path` and `output`:

```yaml
specs:
  - type: openapi
    repo: twilio/twilio-oai
    path_pattern: spec/json/          # fetch every file in this directory
    output_dir: companies/providers/twilio/openapi/
```

## Spec types

| `type` | File extensions | Example |
|--------|----------------|---------|
| `openapi` | `.json`, `.yaml` | Stripe, Twilio, GitHub |
| `graphql` | `.graphql`, `.gql`, `.sdl` | Shopify |
| `grpc` | `.proto` | Google Pub/Sub |
