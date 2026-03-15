.PHONY: notify notify-agent check-consumer raise-issue add-consumer

## notify: run the deterministic consumer notifier (no LLM, no API cost)
##
## Usage:
##   make notify
##
notify:
	GITHUB_TOKEN=$${GITHUB_TOKEN} DRIFTABOT_TOKEN=$${DRIFTABOT_TOKEN} $(PYTHON) -m notifier

## notify-agent: run the LangGraph agent notifier (requires ANTHROPIC_API_KEY)
##
## Usage:
##   make notify-agent
##
notify-agent:
	GITHUB_TOKEN=$${GITHUB_TOKEN} DRIFTABOT_TOKEN=$${DRIFTABOT_TOKEN} ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} $(PYTHON) -m notifier

## check-consumer: check if a GitHub repo uses deprecated or removed API endpoints
##
## Usage:
##   make check-consumer REPO=spree/spree_stripe COMPANY=stripe
##
check-consumer:
	@test -n "$(REPO)"    || (echo "Usage: make check-consumer REPO=owner/repo COMPANY=stripe"; exit 1)
	@test -n "$(COMPANY)" || (echo "Usage: make check-consumer REPO=owner/repo COMPANY=stripe"; exit 1)
	GITHUB_TOKEN=$${GITHUB_TOKEN} $(PYTHON) -m checker --repo $(REPO) --company $(COMPANY)

## add-consumer: check a repo, register it in consumer.companies.yaml, and open an issue if problems found
##
## Usage:
##   make add-consumer REPO=auth0/rules COMPANY=sendgrid
##
add-consumer:
	@test -n "$(REPO)"    || (echo "Usage: make add-consumer REPO=owner/repo COMPANY=stripe"; exit 1)
	@test -n "$(COMPANY)" || (echo "Usage: make add-consumer REPO=owner/repo COMPANY=stripe"; exit 1)
	GITHUB_TOKEN=$${GITHUB_TOKEN} ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} \
	  DRIFTABOT_TOKEN=$${DRIFTABOT_TOKEN} \
	  $(PYTHON) -m checker --repo $(REPO) --company $(COMPANY) --raise-issue --add-consumer

## raise-issue: run checker and open a GitHub issue via DRIFTABOT_TOKEN if issues are found
##
## Usage:
##   make raise-issue REPO=auth0/rules COMPANY=sendgrid
##
raise-issue:
	@test -n "$(REPO)"    || (echo "Usage: make raise-issue REPO=owner/repo COMPANY=stripe"; exit 1)
	@test -n "$(COMPANY)" || (echo "Usage: make raise-issue REPO=owner/repo COMPANY=stripe"; exit 1)
	GITHUB_TOKEN=$${GITHUB_TOKEN} ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} \
	  DRIFTABOT_TOKEN=$${DRIFTABOT_TOKEN} \
	  $(PYTHON) -m checker --repo $(REPO) --company $(COMPANY) --raise-issue
