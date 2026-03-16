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
  - title: Auto-crawled daily
    details: API specs are fetched from each provider's canonical GitHub repository every day at midnight UTC. The crawler runs as a LangGraph agent when ANTHROPIC_API_KEY is set, or as a fast deterministic runner to keep costs low.
  - title: Spec diffs tracked
    details: After each crawl, the @driftabot/engine diff runs against changed specs and saves structured drift results to drifts/ for downstream consumers.
  - title: Automatic consumer notifications
    details: GitHub Code Search finds public repos (≥100 stars) that use a provider's API. Claude semantically analyses each repo's code to detect incorrect or outdated API usage, and opens a GitHub issue via @driftabot-agent.
  - title: Opt-in consumer registry
    details: Register your repo in consumer.companies.yaml to always be scanned by the daily scan-consumers workflow — no search cap, no false negatives from Code Search.
---
