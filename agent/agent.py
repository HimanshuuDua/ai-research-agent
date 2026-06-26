import os
from typing import Literal

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.tools import get_email_tool, get_python_repl_tool, get_web_search_tool

load_dotenv()

ToolMode = Literal["search_only", "search_and_code", "full"]

SYSTEM_PROMPT = """You are a research assistant that takes action — you do not just answer questions.

When given a task:
1. Use web_search to gather current information on the topic.
2. Use python_repl to analyze, summarize, or format the findings when analysis is needed.
3. Use send_email to deliver a clear, well-written summary to the user inbox.

Work step by step. Be thorough but concise in your final email."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)


def _build_tools(mode: ToolMode):
    if mode == "search_only":
        return [get_web_search_tool()]
    if mode == "search_and_code":
        return [get_web_search_tool(), get_python_repl_tool()]
    return [get_web_search_tool(), get_python_repl_tool(), get_email_tool()]


def create_agent(mode: ToolMode = "full") -> AgentExecutor:
    """Build the agent. Start with mode='search_only', then layer in tools."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        google_api_key=os.environ["GOOGLE_API_KEY"],
    )
    tools = _build_tools(mode)
    agent = create_tool_calling_agent(llm, tools, PROMPT)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)


def run_agent(user_input: str, mode: ToolMode = "full", chat_history: list | None = None) -> str:
    executor = create_agent(mode)
    result = executor.invoke({"input": user_input, "chat_history": chat_history or []})
    return result["output"]