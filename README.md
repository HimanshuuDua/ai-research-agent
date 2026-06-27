# AI Research Agent

An AI agent that takes a single text command — like *"Research the latest trends in electric vehicles, run a quick analysis, and email me a summary"* — and executes all three steps automatically.

## What it demonstrates

- **Multi-step reasoning** with LangChain + Gemini
- **Tool use**: web search (SerpAPI), sandboxed Python, email (Resend)
- **Chat UI** in Streamlit with visible agent steps
- **Model fallback** when Gemini free-tier quota is hit

## Tech stack (free-tier friendly)

| Layer | Technology | Free tier |
|-------|------------|-----------|
| Agent brain | LangChain, Gemini 2.5 Flash | Free quota via Google AI Studio |
| Fallback model | Gemini 2.5 Flash Lite | Separate free quota |
| Web search | SerpAPI | 250 searches/month |
| Email | Resend | 3,000 emails/month |
| Chat UI | Streamlit | Free |

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/HimanshuuDua/ai-research-agent.git
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

- `GOOGLE_API_KEY` — [Google AI Studio](https://aistudio.google.com/apikey)
- `SERPAPI_API_KEY` — [SerpAPI](https://serpapi.com/)
- `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_TO_EMAIL` — [Resend](https://resend.com/)

Optional:

- `GEMINI_MODEL` (default: `gemini-2.5-flash`)
- `GEMINI_FALLBACK_MODEL` (default: `gemini-2.5-flash-lite`)

### 3. Verify email (optional)

```bash
python send_test_email.py
```

### 4. Run the website

```bash
streamlit run app.py
```

Open **http://localhost:8501** — type a command, watch the agent work, see results.

## Build order (recommended)

Use the sidebar mode selector:

1. **Web search only** — verify SerpAPI + LangChain agent works
2. **Search + Python REPL** — add sandboxed code execution
3. **Full pipeline** — add email delivery

## Resend email setup

**Testing (no domain needed):**

```env
RESEND_FROM_EMAIL=onboarding@resend.dev
RESEND_TO_EMAIL=your-resend-account@gmail.com
```

With the test sender, Resend only delivers to the email on your Resend account.

**Production:** verify your domain at [resend.com/domains](https://resend.com/domains), then use a `@yourdomain.com` from address.

## Deploy (public demo)

### Streamlit Community Cloud (easiest)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect the repo and set secrets (`GOOGLE_API_KEY`, `SERPAPI_API_KEY`, `RESEND_*`)
4. Main file: `app.py`

### Docker

```bash
docker build -t ai-research-agent .
docker run -p 8501:8501 --env-file .env ai-research-agent
```

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

CI runs lint + tests on push via GitHub Actions.

## Example prompt

```
Research the latest trends in electric vehicles, run a quick analysis, and email me a summary
```

## Project structure

```
agent/
  agent.py          # LangChain agent + run_agent()
  config.py         # env config
  errors.py         # friendly error messages
  llm.py            # Gemini client
  tools/            # web search, python sandbox, email
app.py              # Streamlit chat UI
tests/              # unit tests
```

## License

MIT
