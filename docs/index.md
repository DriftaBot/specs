---
layout: home

hero:
  name: DriftaBot Specs
  text: Public API Spec Registry
  tagline: Always-up-to-date API specifications with automatic breaking change detection and consumer notifications.
  actions:
    - theme: brand
      text: How It Works
      link: /how-it-works
    - theme: brand
      text: Add a Provider
      link: /providers
    - theme: brand
      text: Add a Consumer
      link: /consumers

features:
  - title: Auto-crawled every 6 hours
    details: Specs are fetched from each provider's canonical GitHub repository on a schedule. A LangGraph agent runs at midnight UTC; the other three runs use a fast deterministic crawler to keep costs low.
  - title: Breaking change detection
    details: Every spec update is diffed using the driftabot/engine CLI. Breaking changes are classified by severity and logged to a per-provider drift directory.
  - title: Automatic consumer notifications
    details: When a breaking change is detected, GitHub Code Search finds public repos that use the affected API. A GitHub issue is opened in each affected repo by the @driftabot-agent account.
  - title: Opt-in consumer registry
    details: Register your repo in consumer.companies.yaml to always receive notifications — no search cap, no false positives.
---
