
import streamlit as st
from dotenv import load_dotenv

from agent.agent import run_agent
from agent.config import FALLBACK_MODEL, PRIMARY_MODEL, get_missing_env_keys
from agent.errors import AgentServiceError

load_dotenv()

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
    .step-card {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        background: #f8fafc;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .step-card:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    div[data-testid="stStatusWidget"] { border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AI Research Agent")
st.markdown(
    '<p class="hero">Type one command → search → analyze → email a summary.</p>',
    unsafe_allow_html=True,
)

missing = get_missing_env_keys()
if missing:
    st.error(f"Missing environment variables: {', '.join(missing)}")
    st.info("Copy `.env.example` to `.env` and fill in your API keys.")
    st.stop()

with st.sidebar:
    st.header("Controls")
    mode = st.selectbox(
        "Agent mode",
        options=["full", "search_and_code", "search_only"],
        format_func=lambda m: {
            "search_only": "1. Web search only",
            "search_and_code": "2. Search + Python",
            "full": "3. Full pipeline (+ email)",
        }[m],
    )
    st.caption(f"Primary model: `{PRIMARY_MODEL}`")
    st.caption(f"Fallback model: `{FALLBACK_MODEL}`")
    st.divider()
    st.subheader("Try an example")
    examples = {
        "Research EV trends": "What are the top 3 electric vehicle trends in 2025?",
        "Search + analyze": "Search EV market data and use Python to summarize key stats.",
        "Full pipeline": (
            "Research the latest trends in electric vehicles, "
            "run a quick analysis, and email me a summary"
        ),
    }
    for label, prompt in examples.items():
        if st.button(label, use_container_width=True):
            st.session_state.example_prompt = prompt

    st.divider()
    st.subheader("Resend setup")
    st.caption(
        "Testing: use `onboarding@resend.dev` as sender and your account email as recipient. "
        "For production, verify your domain at resend.com/domains."
    )
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for step in message.get("steps", []):
            with st.expander(f"🔧 {step['tool']}", expanded=False):
                st.markdown("**Input**")
                st.code(step["input"])
                st.markdown("**Output**")
                st.text(step["output"][:1500])
        if message.get("model_used"):
            st.caption(f"Model: `{message['model_used']}`")

prompt = st.chat_input("Research EV trends, analyze them, and email me a summary")
if not prompt and st.session_state.get("example_prompt"):
    prompt = st.session_state.pop("example_prompt")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status = st.status("Agent is working...", expanded=True)
        try:
            history = st.session_state.messages[:-1]
            result = run_agent(prompt, mode=mode, chat_history=history)

            for step in result.steps:
                status.write(f"**{step.tool}** completed")
                with st.expander(f"🔧 {step.tool}", expanded=False):
                    st.markdown("**Input**")
                    st.code(step.input)
                    st.markdown("**Output**")
                    st.text(step.output[:1500])

            status.update(label="Done", state="complete", expanded=False)
            st.markdown(result.output or "Task completed.")
            st.caption(f"Model: `{result.model_used}`")

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result.output or "Task completed.",
                    "steps": [
                        {"tool": s.tool, "input": s.input, "output": s.output}
                        for s in result.steps
                    ],
                    "model_used": result.model_used,
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
