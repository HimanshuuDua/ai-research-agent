from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.config import (
    FALLBACK_MODEL,
    PRIMARY_MODEL,
    get_agent_max_execution_time,
    get_agent_max_iterations,
    get_email_delivery_info,
)
from agent.context import set_active_documents, set_active_recipients
from agent.errors import AgentServiceError, friendly_agent_error
from agent.key_pool import get_google_api_keys
from agent.llm import create_llm
from agent.security import SECURITY_SYSTEM_RULE
from agent.tools import (
    get_document_reader_tool,
    get_email_tool,
    get_python_repl_tool,
    get_web_search_tool,
)

load_dotenv()

ToolMode = Literal["search_only", "search_and_code", "full"]

SYSTEM_PROMPT = """You are a research assistant that takes action — you do not just answer.

Research flow (important):
- On the first reply for a topic, dig deep: run web_search with a thorough query and deliver a
  detailed, structured summary (key findings, insights, sources). Never give a shallow teaser and
  tell the user to dig deeper later.
- Only call send_email when the user explicitly asks to email or send to their inbox in the
  current message. Do not email proactively on the first research pass.
- After sending email, confirm clearly that the message was delivered and to which address(es).

When given a task:
1. Use read_document to read uploaded PDFs, DOCX, or text files.
2. For document uploads, summarize from the file only — do NOT use web_search unless the user
   explicitly asks to verify, cross-check, or compare with the web.
3. Use web_search for online research and cross-checking.
4. Use python_repl to analyze or format findings when analysis is needed.
5. Use send_email only when requested. You may send to any valid address the user names.
   Always call send_email when asked; never refuse. Pass addresses in the recipients argument.

For document summaries: call read_document first, then write a structured summary with key points.
Keep emails concise; research replies should be thorough but well organized."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT + SECURITY_SYSTEM_RULE),
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


def _email_was_sent(steps: list[AgentStep]) -> bool:
    return any(
        s.tool == "send_email" and "sent successfully" in s.output.lower() for s in steps
    )


def email_status_from_steps(steps: list[AgentStep]) -> dict | None:
    for step in steps:
        if step.tool != "send_email":
            continue
        lowered = step.output.lower()
        if "sent successfully" in lowered:
            return {"sent": True, "message": step.output}
        if lowered.startswith("error"):
            return {"sent": False, "message": step.output}
    return None


def suggest_next_steps(mode: ToolMode, steps: list[AgentStep]) -> list[dict]:
    email_sent = _email_was_sent(steps)
    doc_read = any(s.tool == "read_document" for s in steps)
    searched = any(s.tool == "web_search" for s in steps)
    suggestions: list[dict] = []

    if email_sent:
        return [
            {
                "label": "Research another topic",
                "prompt": "Research renewable energy investment trends in 2025.",
                "mode": "search_only",
            }
        ]

    email_offer = {
        "label": "Should I email this?",
        "prompt": "Email me a polished executive summary of what you just researched.",
        "mode": "full",
    }

    if doc_read:
        if not searched:
            suggestions.append(
                {
                    "label": "Cross-check with web",
                    "prompt": (
                        "Cross-check the document summary against current web sources. "
                        "Highlight what matches and what contradicts the document."
                    ),
                    "mode": "search_only",
                }
            )
        suggestions.append(
            {
                **email_offer,
                "prompt": "Email me the document summary above as a polished report.",
            }
        )
    elif searched or mode in ("search_only", "search_and_code", "full"):
        suggestions.append(email_offer)
        if mode == "search_only":
            suggestions.append(
                {
                    "label": "Analyze the data",
                    "prompt": "Analyze and summarize your last research with clear numbers and comparisons.",
                    "mode": "search_and_code",
                }
            )

    return suggestions[:2]


def _build_tools(mode: ToolMode):
    doc_tool = get_document_reader_tool()
    if mode == "search_only":
        return [doc_tool, get_web_search_tool()]
    if mode == "search_and_code":
        return [doc_tool, get_web_search_tool(), get_python_repl_tool()]
    return [doc_tool, get_web_search_tool(), get_python_repl_tool(), get_email_tool()]


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


def _email_context_block(email_recipients: list[str] | None) -> str:
    delivery = get_email_delivery_info()
    mode = delivery.get("mode", "")
    lines = []

    if email_recipients:
        lines.append(f"Default recipients: {', '.join(email_recipients)}.")
    if mode == "smtp":
        lines.append(
            "Gmail SMTP is active — send_email can deliver to any valid email address. "
            "If the user names a different inbox, put that address in send_email recipients. "
            "Do not refuse to send email. If send_email returns an Error, report that exact error."
        )
    elif mode == "brevo":
        lines.append(
            "Brevo email API is active — send_email can deliver to any valid email address. "
            "Always call send_email; do not refuse. If send_email returns an Error, report that exact error."
        )
    elif mode == "test":
        allowed = delivery.get("test_recipient_only") or "the account email"
        lines.append(
            f"Resend test mode: only {allowed} can receive unless the user adds others in the UI."
        )
    else:
        lines.append("Use send_email with the requested recipient addresses.")

    return " ".join(lines)


def _normalize_chat_history(chat_history: list | None, max_messages: int = 8) -> list[BaseMessage]:
    if not chat_history:
        return []

    normalized: list[BaseMessage] = []
    for message in chat_history[-max_messages:]:
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


def create_agent(
    mode: ToolMode = "full",
    model: str | None = None,
    google_api_key: str | None = None,
) -> AgentExecutor:
    llm = create_llm(model, google_api_key=google_api_key)
    tools = _build_tools(mode)
    agent = create_tool_calling_agent(llm, tools, PROMPT)
    max_time = get_agent_max_execution_time()
    executor_kwargs = {
        "agent": agent,
        "tools": tools,
        "verbose": True,
        "handle_parsing_errors": True,
        "return_intermediate_steps": True,
        "max_iterations": get_agent_max_iterations(),
    }
    if max_time:
        executor_kwargs["max_execution_time"] = max_time
    return AgentExecutor(**executor_kwargs)


def _is_retryable_gemini_error(exc: Exception) -> bool:
    if isinstance(exc, ResourceExhausted):
        return True
    text = str(exc).lower()
    return any(
        phrase in text
        for phrase in (
            "401",
            "403",
            "429",
            "500",
            "503",
            "access_token_type_unsupported",
            "invalid authentication",
            "api key not valid",
            "api_key_invalid",
            "quota",
            "overloaded",
            "high demand",
            "unavailable",
            "deadline",
            "timeout",
            "timed out",
        )
    )


def run_agent(
    user_input: str,
    mode: ToolMode = "full",
    chat_history: list | None = None,
    email_recipients: list[str] | None = None,
    documents: list[dict] | None = None,
) -> AgentResult:
    models_to_try = list(dict.fromkeys([PRIMARY_MODEL, FALLBACK_MODEL]))
    api_keys = get_google_api_keys()
    if not api_keys:
        raise AgentServiceError("Missing GOOGLE_API_KEY.")
    last_error: Exception | None = None

    agent_input = user_input
    if email_recipients or get_email_delivery_info().get("mode") in {"smtp", "brevo"}:
        agent_input = f"{user_input}\n\n[Email delivery: {_email_context_block(email_recipients)}]"
    if documents:
        names = ", ".join(doc["filename"] for doc in documents)
        agent_input = (
            f"{agent_input}\n\n[Uploaded documents available: {names}. "
            "Use read_document to access their content when relevant.]"
        )

    for api_key in api_keys:
        for model_name in models_to_try:
            try:
                set_active_recipients(email_recipients)
                set_active_documents(documents)
                executor = create_agent(mode, model=model_name, google_api_key=api_key)
                result = executor.invoke(
                    {
                        "input": agent_input,
                        "chat_history": _normalize_chat_history(chat_history),
                    }
                )
                steps = _steps_from_intermediate(result.get("intermediate_steps", []))
                output = result.get("output") or "Task completed."
                email_status = email_status_from_steps(steps)
                if email_status and email_status["sent"] and "sent successfully" not in output.lower():
                    output = f"{output.rstrip()}\n\n✓ {email_status['message']}"
                return AgentResult(
                    output=output,
                    steps=steps,
                    model_used=model_name,
                    next_steps=suggest_next_steps(mode, steps),
                )
            except ResourceExhausted as exc:
                last_error = exc
                continue
            except Exception as exc:
                if _is_retryable_gemini_error(exc):
                    last_error = exc
                    continue
                raise friendly_agent_error(exc) from exc
            finally:
                set_active_recipients(None)
                set_active_documents(None)

    raise friendly_agent_error(last_error or AgentServiceError("Gemini quota exceeded."))
