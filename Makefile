# Load .env if present (never committed — see .gitignore)
-include .env
export

PYTHON := $(shell command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3 || command -v python)

include make/git.mk
include make/release.mk
include make/crawler.mk
