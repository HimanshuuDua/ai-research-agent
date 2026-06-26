# AI Research Agent

An AI agent that takes a single text command — like *"Research the latest trends in electric vehicles, run a quick analysis, and email me a summary"* — and executes all three steps automatically.

## What it demonstrates

- **Multi-step reasoning** with LangChain + GPT-4o
- **Tool use**: web search (SerpAPI), Python REPL, email (SendGrid)
- **Chat UI** in Streamlit (~50 lines, no React needed)

## Tech stack

| Layer | Technology |
|-------|------------|
| Agent brain | LangChain, OpenAI GPT-4o |
| Tools | SerpAPI, Python REPL, SendGrid |
| Chat UI | Streamlit |
| Backend | Python |

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/111205255/ai-research-agent.git
cd ai-research-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
copy .env.example .env
```

Fill in `.env`:

- `OPENAI_API_KEY` — OpenAI
- `SERPAPI_API_KEY` — SerpAPI
- `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `SENDGRID_TO_EMAIL` — SendGrid

### 3. Run the app

```bash
streamlit run app.py
```

## Build order (recommended)

Do not wire all three tools at once. Use the sidebar mode selector:

1. **Web search only** — verify SerpAPI + LangChain agent works
2. **Search + Python REPL** — add code execution
3. **Full pipeline** — add email delivery

## Example prompt

```
Research the latest trends in electric vehicles, run a quick analysis, and email me a summary
```

## Project structure

```
ai-research-agent/
├── app.py
├── agent/
│   ├── agent.py
│   └── tools/
│       ├── web_search.py
│       ├── python_repl.py
│       └── email.py
├── requirements.txt
└── .env.example
```

## License

MIT
