"""
LangGraph ReAct agent for crawling public API specs from GitHub.
"""
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from crawler.tools import ALL_TOOLS

SYSTEM_PROMPT = """You are an API spec crawler agent. Your job is to keep this repository
up-to-date with the latest public API specifications (OpenAPI, GraphQL, gRPC) from major
companies' public GitHub repositories.

## Instructions

1. Call `load_companies_config` to get the list of all companies and their spec entries.

2. For each company and each spec entry:
   a. If the entry has a `path` and `output` field:
      Call `sync_spec(repo=entry.repo, repo_path=entry.path, output_path=entry.output)`.

   b. If the entry has a `path_pattern` and `output_dir` field (fetch a whole directory):
      - Call `list_repo_directory(repo=entry.repo, path=entry.path_pattern)` to get the file list.
      - For each file, call `sync_spec(repo=entry.repo, repo_path=file.path, output_path=entry.output_dir + file.name)`.

3. Continue processing ALL companies and specs even if one fails — never abort early.

4. After processing everything, print a summary:
   - How many specs were updated
   - How many were unchanged
   - How many errored (with company name and error message)

## Important rules
- Only write files under the `companies/` directory.
- Do not read or display spec file contents — `sync_spec` handles fetch+compare+write internally.
"""


def build_agent():
    model = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=8096)
    return create_react_agent(model=model, tools=ALL_TOOLS, prompt=SYSTEM_PROMPT)
