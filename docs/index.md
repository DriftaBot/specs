---
layout: home

hero:
  name: DriftaBot Registry
  text: Public API Spec Registry
  tagline: Always-up-to-date API specifications, crawled daily from canonical provider repositories and diffed for breaking changes.
  actions:
    - theme: brand
      text: How It Works
      link: /how-it-works
    - theme: brand
      text: Add a Provider
      link: /providers

features:
  - title: Auto-crawled daily
    details: API specs are fetched from each provider's canonical GitHub repository every day at midnight UTC. The crawler runs as a LangGraph agent when ANTHROPIC_API_KEY is set, or as a fast deterministic runner to keep costs low.
  - title: Spec diffs tracked
    details: After each crawl, the @driftabot/engine diff runs against changed specs and saves structured drift results to drifts/ for downstream use.
  - title: 59 providers and counting
    details: OpenAPI, GraphQL, and gRPC specs from Stripe, Twilio, GitHub, Slack, SendGrid, DigitalOcean, and dozens more — all in one place.
  - title: Open and extensible
    details: Add a new provider by opening a pull request. The crawler picks it up automatically on its next run.
---
