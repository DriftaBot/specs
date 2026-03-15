# Load .env if present (never committed — see .gitignore)
-include .env
export

include make/git.mk
include make/release.mk
include make/crawler.mk
include make/notifier.mk
