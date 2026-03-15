.PHONY: crawl crawl-agent

## crawl: run the deterministic crawler (no LLM, no API cost)
##
## Usage:
##   make crawl
##
crawl:
	GITHUB_TOKEN=$${GITHUB_TOKEN} $(PYTHON) -m crawler

## crawl-agent: run the LangGraph agent crawler (requires ANTHROPIC_API_KEY)
##
## Usage:
##   make crawl-agent
##
crawl-agent:
	GITHUB_TOKEN=$${GITHUB_TOKEN} ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} $(PYTHON) -m crawler
