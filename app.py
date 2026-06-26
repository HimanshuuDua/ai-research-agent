import os

import streamlit as st
from dotenv import load_dotenv

from agent.agent import run_agent

load_dotenv()

st.set_page_config(page_title="AI Research Agent", page_icon="🤖", layout="centered")

st.title("AI Research Agent")
st.caption(
    "One command → search the web → run analysis → email a summary. "
    "Built with LangChain, GPT-4o, SerpAPI, and SendGrid."
)

REQUIRED_KEYS = [
    "OPENAI_API_KEY",
    "SERPAPI_API_KEY",
    "SENDGRID_API_KEY",
    "SENDGRID_FROM_EMAIL",
    "SENDGRID_TO_EMAIL",
]
missing = [key for key in REQUIRED_KEYS if not os.getenv(key)]
if missing:
    st.error(f"Missing environment variables: {', '.join(missing)}")
    st.info("Copy `.env.example` to `.env` and fill in your API keys.")
    st.stop()

mode = st.sidebar.selectbox(
    "Agent mode (build incrementally)",
    options=["full", "search_and_code", "search_only"],
    format_func=lambda m: {
        "search_only": "1. Web search only",
        "search_and_code": "2. Search + Python REPL",
        "full": "3. Full pipeline (+ email)",
    }[m],
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Research EV trends, analyze them, and email me a summary"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent is thinking and calling tools..."):
            try:
                response = run_agent(prompt, mode=mode)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as exc:
                st.error(f"Agent error: {exc}")
