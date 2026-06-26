# AI Research Agent

An AI agent that takes a single text command — like *"Research the latest trends in electric vehicles, run a quick analysis, and email me a summary"* — and executes all three steps automatically.

## What it demonstrates

- **Multi-step reasoning** with LangChain + Gemini 2.5 Flash
- **Tool use**: web search (SerpAPI), Python REPL, email (Resend)
- **Chat UI** in Streamlit (~50 lines, no React needed)

## Tech stack (free-tier friendly)

| Layer | Technology | Free tier |
|-------|------------|-----------|
| Agent brain | LangChain, Gemini 2.5 Flash | Free quota via Google AI Studio |
| Web search | SerpAPI | 250 searches/month |
| Email | Resend | 3,000 emails/month (permanent) |
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

- `GOOGLE_API_KEY` — [Google AI Studio](https://aistudio.google.com/apikey) (Gemini 2.5 Flash)
- `SERPAPI_API_KEY` — [SerpAPI](https://serpapi.com/) (250 free searches/month)
- `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_TO_EMAIL` — [Resend](https://resend.com/) (3,000 free emails/month)

For Resend testing, you can use `onboarding@resend.dev` as the from address until you verify your own domain.

### 3. Run the app

```bash
streamlit run app.py
```

## Build order (recommended)

Use the sidebar mode selector:

1. **Web search only** — verify SerpAPI + LangChain agent works
2. **Search + Python REPL** — add code execution
3. **Full pipeline** — add email delivery

## Example prompt

```
Research the latest trends in electric vehicles, run a quick analysis, and email me a summary
```

## Why Resend instead of SendGrid?

SendGrid removed its permanent free plan in 2025 (60-day trial only). Resend offers a **permanent** free tier: 3,000 emails/month, 100/day.

## License

MIT