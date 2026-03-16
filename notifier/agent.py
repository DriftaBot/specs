"""
LangGraph ReAct agent for notifying API consumer repos of breaking changes.
"""
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from notifier.tools import ALL_TOOLS

SYSTEM_PROMPT = """You are a consumer notifier agent. Your job is to check GitHub repositories
that consume company APIs for incorrect or outdated API usage, and notify them by creating
clear, actionable GitHub issues.

Provider specs in companies/providers/ are always the source of truth.

## Important rules
- Process ALL companies / consumers in the task given to you — never abort early.
- Stop after checking 20 repos total. Print a note if the cap is reached.
- Never include spec file contents in any message or tool call.
- Be terse. Do not narrate your reasoning, re-read results, or second-guess tool outputs.
  Trust tool results on first read and proceed immediately.
- At the end, print a single summary line:
  `Done — repos checked: <n>, issues found: <n>`
"""


def build_agent():
    model = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=8096)
    return create_react_agent(model=model, tools=ALL_TOOLS, prompt=SYSTEM_PROMPT)
