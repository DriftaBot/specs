---
layout: home

hero:
  name: DriftaBot Registry
  text: Public API Spec Registry
  tagline: Always-up-to-date API specifications. Consumer repos are checked directly against current provider specs and notified when their API usage is incorrect or outdated.
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
    details: API specs are fetched from each provider's canonical GitHub repository on a schedule. A LangGraph agent runs at midnight UTC; the other three runs use a fast deterministic crawler to keep costs low.
  - title: Specs as source of truth
    details: Provider specs in companies/providers/ are always current. No spec diffing or change tracking needed — the notifier checks consumer code directly against the latest spec on every run.
  - title: Automatic consumer notifications
    details: GitHub Code Search finds public repos that use a provider's API. Claude semantically analyses each repo's code to detect incorrect or outdated API usage, and opens a GitHub issue via @driftabot-agent.
  - title: Opt-in consumer registry
    details: Register your repo in consumer.companies.yaml to always be checked — no search cap, no false negatives from Code Search.
---
