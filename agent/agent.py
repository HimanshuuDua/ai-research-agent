from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.config import FALLBACK_MODEL, PRIMARY_MODEL
from agent.errors import AgentServiceError, friendly_agent_error
from agent.llm import create_llm
from agent.tools import get_email_tool, get_python_repl_tool, get_web_search_tool

load_dotenv()

ToolMode = Literal["search_only", "search_and_code", "full"]

SYSTEM_PROMPT = """You are a research assistant that takes action — you do not just answer.

When given a task:
1. Use web_search to gather current information on the topic.
2. Use python_repl to analyze, summarize, or format the findings when analysis is needed.
3. Use send_email to deliver a clear summary to the user inbox when email is requested.
   Emails go to the configured recipient list unless the user asks to add more addresses.

Work step by step. Be thorough but concise in your final response and email."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)


@dataclass
class AgentStep:
    tool: str
    input: str
    output: str


@dataclass
class AgentResult:
    output: str
    steps: list[AgentStep] = field(default_factory=list)
    model_used: str = PRIMARY_MODEL
    next_steps: list[dict] = field(default_factory=list)


def suggest_next_steps(mode: ToolMode, steps: list[AgentStep]) -> list[dict]:
    email_sent = any(
        s.tool == "send_email" and "sent successfully" in s.output.lower() for s in steps
    )
    suggestions: list[dict] = []

    if mode == "search_only":
        suggestions.extend(
            [
                {
                    "label": "Analyze with Python",
                    "prompt": "Use Python to analyze and summarize your last search findings.",
                    "mode": "search_and_code",
                },
                {
                    "label": "Email me a summary",
                    "prompt": "Email me a polished executive summary of what you just researched.",
                    "mode": "full",
                },
            ]
        )
    elif mode == "search_and_code" and not email_sent:
        suggestions.append(
            {
                "label": "Email this report",
                "prompt": "Send the analysis above to my inbox as a formatted email.",
                "mode": "full",
            }
        )
    elif mode == "full" and email_sent:
        suggestions.append(
            {
                "label": "Research another topic",
                "prompt": "Research the latest AI agent trends in 2025 and email me a summary.",
                "mode": "full",
            }
        )

    suggestions.append(
        {
            "label": "Dig deeper",
            "prompt": "Search for more data on this topic and highlight the top 5 insights.",
            "mode": mode,
        }
    )
    return suggestions[:3]


def _build_tools(mode: ToolMode):
    if mode == "search_only":
        return [get_web_search_tool()]
    if mode == "search_and_code":
        return [get_web_search_tool(), get_python_repl_tool()]
    return [get_web_search_tool(), get_python_repl_tool(), get_email_tool()]


def _steps_from_intermediate(intermediate_steps: list) -> list[AgentStep]:
    parsed: list[AgentStep] = []
    for action, observation in intermediate_steps:
        tool_input = action.tool_input
        if isinstance(tool_input, dict):
            input_text = ", ".join(f"{k}={v!r}" for k, v in tool_input.items())
        else:
            input_text = str(tool_input)
        parsed.append(
            AgentStep(
                tool=action.tool,
                input=input_text[:500],
                output=str(observation)[:2000],
            )
        )
    return parsed


def _normalize_chat_history(chat_history: list | None) -> list[BaseMessage]:
    if not chat_history:
        return []

    normalized: list[BaseMessage] = []
    for message in chat_history:
        if isinstance(message, (HumanMessage, AIMessage)):
            normalized.append(message)
            continue
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            normalized.append(HumanMessage(content=content))
        elif role == "assistant":
            normalized.append(AIMessage(content=content))
    return normalized


def create_agent(mode: ToolMode = "full", model: str | None = None) -> AgentExecutor:
    llm = create_llm(model)
    tools = _build_tools(mode)
    agent = create_tool_calling_agent(llm, tools, PROMPT)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
        max_iterations=10,
    )


def run_agent(
    user_input: str,
    mode: ToolMode = "full",
    chat_history: list | None = None,
) -> AgentResult:
    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
    last_error: Exception | None = None

    for model_name in models_to_try:
        try:
            executor = create_agent(mode, model=model_name)
            result = executor.invoke(
                {
                    "input": user_input,
                    "chat_history": _normalize_chat_history(chat_history),
                }
            )
            steps = _steps_from_intermediate(result.get("intermediate_steps", []))
            return AgentResult(
                output=result.get("output") or "Task completed.",
                steps=steps,
                model_used=model_name,
                next_steps=suggest_next_steps(mode, steps),
            )
        except ResourceExhausted as exc:
            last_error = exc
            if model_name == FALLBACK_MODEL:
                break
            continue
        except Exception as exc:
            raise friendly_agent_error(exc) from exc

    raise friendly_agent_error(last_error or AgentServiceError("Gemini quota exceeded."))
