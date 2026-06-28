
import streamlit as st
from dotenv import load_dotenv

from agent.agent import run_agent
from agent.config import FALLBACK_MODEL, PRIMARY_MODEL, get_email_recipients, get_missing_env_keys
from agent.context import parse_recipient_string
from agent.documents import extract_document
from agent.errors import AgentServiceError

load_dotenv()

MODE_OPTIONS = ["full", "search_and_code", "search_only"]
MODE_LABELS = {
    "search_only": "1. Web search only",
    "search_and_code": "2. Search + Python",
    "full": "3. Full pipeline (+ email)",
}

DOC_PLACEHOLDER = "What should I do with this document? e.g. Summarize it, cross-check with web…"

STARTER_PROMPTS = [
    {
        "label": "Research EV trends",
        "prompt": "What are the top 3 electric vehicle trends in 2025?",
        "mode": "search_only",
    },
    {
        "label": "Search + analyze",
        "prompt": "Search EV market data and use Python to summarize key stats.",
        "mode": "search_and_code",
    },
    {
        "label": "Full pipeline",
        "prompt": (
            "Research the latest trends in electric vehicles, "
            "run a quick analysis, and email me a summary"
        ),
        "mode": "full",
    },
    {
        "label": "Compare AI tools",
        "prompt": "Research the top AI agent frameworks in 2025 and compare their strengths.",
        "mode": "search_only",
    },
]

st.set_page_config(
    page_title="AI Research Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 1.5rem; max-width: 960px; }
    .hero { color: #64748b; margin-bottom: 1.5rem; animation: fadeIn 0.6s ease; }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    div[data-testid="stStatusWidget"] { border-radius: 12px; }
    [data-testid="stFileUploader"] {
        border: 1px dashed #cbd5e1;
        border-radius: 12px;
        padding: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AI Research Agent")
st.markdown(
    '<p class="hero">Drag a document into the chat, type your instruction, then press Enter.</p>',
    unsafe_allow_html=True,
)

missing = get_missing_env_keys()
if missing:
    st.error(f"Missing environment variables: {', '.join(missing)}")
    st.info("Copy `.env.example` to `.env` and fill in your API keys.")
    st.stop()

if "agent_mode" not in st.session_state:
    st.session_state.agent_mode = "full"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "processed_uploads" not in st.session_state:
    st.session_state.processed_uploads = set()


def queue_prompt(prompt: str, mode: str | None = None) -> None:
    st.session_state.example_prompt = prompt
    if mode:
        st.session_state.agent_mode = mode


def render_next_steps(next_steps: list[dict], key_prefix: str) -> None:
    if not next_steps:
        return
    st.markdown("**Suggested next step**")
    cols = st.columns(len(next_steps))
    for col, step in zip(cols, next_steps):
        if col.button(step["label"], key=f"{key_prefix}_{step['label']}", use_container_width=True):
            queue_prompt(step["prompt"], step.get("mode"))
            st.rerun()


def run_agent_turn(prompt: str, *, user_display: str | None = None) -> None:
    display = user_display if user_display is not None else prompt
    st.session_state.messages.append({"role": "user", "content": display})
    with st.chat_message("user"):
        st.markdown(display)

    with st.chat_message("assistant"):
        status = st.status("Agent is working...", expanded=True)
        try:
            history = st.session_state.messages[:-1]
            raw = st.session_state.get("email_recipients", "")
            recipients = parse_recipient_string(raw) or None
            documents = st.session_state.documents or None
            result = run_agent(
                prompt,
                mode=st.session_state.agent_mode,
                chat_history=history,
                email_recipients=recipients,
                documents=documents,
            )

            for step in result.steps:
                status.write(f"**{step.tool}** completed")
                with st.expander(f"Tool · {step.tool}", expanded=False):
                    st.markdown("**Input**")
                    st.code(step.input)
                    st.markdown("**Output**")
                    st.text(step.output[:1500])

            status.update(label="Done", state="complete", expanded=False)
            st.markdown(result.output or "Task completed.")
            st.caption(f"Model: `{result.model_used}`")
            render_next_steps(result.next_steps, "live")

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result.output or "Task completed.",
                    "steps": [
                        {"tool": s.tool, "input": s.input, "output": s.output}
                        for s in result.steps
                    ],
                    "model_used": result.model_used,
                    "next_steps": result.next_steps,
                }
            )
        except AgentServiceError as exc:
            status.update(label="Failed", state="error")
            st.error(str(exc))
            if exc.hint:
                st.info(exc.hint)
        except Exception as exc:
            status.update(label="Failed", state="error")
            st.error(f"Unexpected error: {exc}")


with st.sidebar:
    st.header("Controls")

    mode = st.selectbox(
        "Agent mode",
        options=MODE_OPTIONS,
        index=MODE_OPTIONS.index(st.session_state.agent_mode),
        format_func=lambda m: MODE_LABELS[m],
        key="mode_select",
    )
    st.session_state.agent_mode = mode

    st.caption(f"Primary model: `{PRIMARY_MODEL}`")
    st.caption(f"Fallback model: `{FALLBACK_MODEL}`")
    st.divider()

    st.subheader("Email recipients")
    default_recipients = ", ".join(get_email_recipients())
    st.session_state.email_recipients = st.text_area(
        "Send summaries to (comma-separated)",
        value=st.session_state.get("email_recipients", default_recipients),
        height=68,
        help="Change who receives email summaries for this session.",
    )

    st.divider()
    st.subheader("Try an example")
    for item in STARTER_PROMPTS:
        if st.button(item["label"], use_container_width=True, key=f"side_{item['label']}"):
            queue_prompt(item["prompt"], item["mode"])
            st.rerun()

    st.divider()
    st.caption(
        "Testing: use `onboarding@resend.dev` as sender. "
        "Verify your domain at resend.com/domains for other recipients."
    )
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.documents = []
        st.session_state.processed_uploads = set()
        st.rerun()

for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for step in message.get("steps", []):
            with st.expander(f"Tool · {step['tool']}", expanded=False):
                st.markdown("**Input**")
                st.code(step["input"])
                st.markdown("**Output**")
                st.text(step["output"][:1500])
        if message.get("model_used"):
            st.caption(f"Model: `{message['model_used']}`")
        if message["role"] == "assistant":
            render_next_steps(message.get("next_steps", []), f"hist_{index}")

if not st.session_state.messages:
    st.markdown("#### Pick a starter")
    cols = st.columns(2)
    for i, item in enumerate(STARTER_PROMPTS):
        with cols[i % 2]:
            if st.button(item["label"], key=f"starter_{i}", use_container_width=True):
                queue_prompt(item["prompt"], item["mode"])
                st.rerun()

uploaded_files = st.file_uploader(
    "Drop a PDF, DOCX, or text file here to attach",
    type=["pdf", "docx", "txt", "md", "csv", "json", "html", "rtf"],
    accept_multiple_files=True,
    help="Legacy .doc is not supported. Save as .docx or PDF, then type your instruction.",
)
if uploaded_files:
    for file in uploaded_files:
        if file.name in st.session_state.processed_uploads:
            continue
        try:
            extracted = extract_document(file.read(), file.name)
            st.session_state.documents = [
                doc for doc in st.session_state.documents if doc["filename"] != file.name
            ]
            st.session_state.documents.append(
                {
                    "filename": extracted.filename,
                    "text": extracted.text,
                    "char_count": extracted.char_count,
                    "truncated": extracted.truncated,
                    "format": extracted.format,
                }
            )
            st.session_state.processed_uploads.add(file.name)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

if st.session_state.documents:
    st.caption("Attached documents:")
    for doc in st.session_state.documents:
        suffix = " (truncated)" if doc.get("truncated") else ""
        st.markdown(f"- `{doc['filename']}` · {doc['char_count']} chars{suffix}")
    if st.button("Remove attachments", key="clear_docs"):
        st.session_state.documents = []
        st.session_state.processed_uploads = set()
        st.rerun()
    st.info("Type what you want the AI to do with the file(s), then press Enter.")

chat_placeholder = DOC_PLACEHOLDER if st.session_state.documents else (
    "Research EV trends, analyze them, and email me a summary"
)
prompt = st.chat_input(chat_placeholder)
if not prompt and st.session_state.get("example_prompt"):
    prompt = st.session_state.pop("example_prompt")

if prompt:
    display = prompt
    if st.session_state.documents:
        names = ", ".join(doc["filename"] for doc in st.session_state.documents)
        display = f"{prompt}\n\n[Attached: {names}]"
    run_agent_turn(prompt, user_display=display)
