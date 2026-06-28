# AI Research Agent

An AI agent that takes one command — research, analyze, summarize documents, and email results — and runs the full pipeline automatically.

**Live demo:** https://ai-research-agent-ecru-zeta.vercel.app

---

## Table of contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Quick start (local)](#quick-start-local)
4. [Environment variables](#environment-variables)
5. [Email setup — test vs production](#email-setup--test-vs-production)
6. [Usage guide](#usage-guide)
7. [Deploy to Vercel](#deploy-to-vercel)
8. [Project structure](#project-structure)
9. [Development](#development)
10. [Troubleshooting](#troubleshooting)

---

## Features

| Feature | Description |
|---------|-------------|
| Web search | Current info via SerpAPI |
| Python analysis | Sandboxed REPL for stats and formatting |
| Document upload | Drag PDF, DOCX, or text into chat — you choose the prompt |
| Email delivery | Send summaries via Resend |
| Chat UI | Web (Vercel) + Streamlit (local) |
| Model fallback | Switches to `gemini-2.5-flash-lite` on quota errors |

---

## Tech stack

| Layer | Technology | Free tier |
|-------|------------|-----------|
| Agent | LangChain + Gemini 2.5 Flash | [Google AI Studio](https://aistudio.google.com/apikey) |
| Fallback model | Gemini 2.5 Flash Lite | Separate quota |
| Search | SerpAPI | 250 searches/month |
| Email | Resend | 3,000 emails/month |
| Web UI | FastAPI + static HTML | Vercel free tier |
| Local UI | Streamlit | Free |

---

## Quick start (local)

```bash
git clone https://github.com/HimanshuuDua/ai-research-agent.git
cd ai-research-agent
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
copy .env.example .env          # fill in API keys
streamlit run app.py
```

Open **http://localhost:8501**

Verify email:

```bash
python send_test_email.py
```

---

## Environment variables

Copy `.env.example` → `.env` and set:

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `SERPAPI_API_KEY` | Yes | Web search |
| `EMAIL_PROVIDER` | No | `smtp` (recommended) or `resend` |
| `SMTP_USER` | SMTP mode | Your Gmail address |
| `SMTP_PASSWORD` | SMTP mode | Google App Password (16 chars) |
| `SMTP_FROM` | No | Display name, e.g. `AI Agent <you@gmail.com>` |
| `RESEND_API_KEY` | Resend mode | Resend API key |
| `RESEND_FROM_EMAIL` | Resend mode | Sender address |
| `RESEND_TO_EMAIL` | Yes | Default recipient(s), comma-separated |
| `RESEND_ACCOUNT_EMAIL` | Resend test | Your Resend login email |
| `GEMINI_MODEL` | No | Default: `gemini-2.5-flash` |
| `GEMINI_FALLBACK_MODEL` | No | Default: `gemini-2.5-flash-lite` |

**Never commit `.env` to GitHub.**

---

## Email setup — send to anyone (no domain verification)

### Recommended: Gmail SMTP

Send to **any email address** using your Gmail account — no domain verification required.

1. Turn on **2-Step Verification** on your Google account
2. Create an **App Password**: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Add to `.env` (and Vercel env vars for the live site):

```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-char-google-app-password
SMTP_FROM=AI Research Agent <you@gmail.com>
RESEND_TO_EMAIL=you@gmail.com, teammate@company.com
```

4. Test: `python send_test_email.py`
5. In the UI sidebar, **Add** any receiver emails — they will all receive mail

### Alternative: Resend (limited without domain)

Resend’s test sender `onboarding@resend.dev` only delivers to your Resend account email.

```env
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=onboarding@resend.dev
RESEND_ACCOUNT_EMAIL=you@gmail.com
```

To email anyone with Resend, verify a domain at [resend.com/domains](https://resend.com/domains) and use `@yourdomain.com` as the sender.

---

## Usage guide

### Agent modes (sidebar)

| Mode | Tools available |
|------|-----------------|
| 1 · Web search only | Search + read documents |
| 2 · Search + Python | Search + code + documents |
| 3 · Full pipeline (+ email) | All tools including **send_email** |

**Email only works in mode 3.**

### Documents

1. Drag a PDF/DOCX into the chat area
2. File attaches above the input — nothing sends yet
3. Type what you want: *“Summarize this”*, *“Cross-check with web”*, etc.
4. Click **Send**

### Example prompts

```
Research the latest trends in electric vehicles, run a quick analysis, and email me a summary
```

```
Send me a test email with subject Hello and body It works.
```

```
Cross-check the document summary against current web sources.
```

---

## Deploy to Vercel

1. Push to GitHub (see below)
2. Import repo at [vercel.com/new](https://vercel.com/new)
3. Set environment variables (same as `.env`)
4. Deploy

**Production URL:** https://ai-research-agent-ecru-zeta.vercel.app

```bash
vercel deploy --prod
```

**Note:** Vercel free tier has ~10s function timeout. Long research + email runs may timeout — use Streamlit locally or Vercel Pro for 60s.

### Docker (optional)

```bash
docker build -t ai-research-agent .
docker run -p 8501:8501 --env-file .env ai-research-agent
```

---

## Project structure

```
ai-research-agent/
├── agent/
│   ├── agent.py              # LangChain agent, modes, next-step suggestions
│   ├── config.py             # Env config, email test/production detection
│   ├── context.py            # Session recipients + documents
│   ├── documents.py          # PDF/DOCX/text extraction
│   ├── errors.py             # User-friendly API errors
│   ├── llm.py                # Gemini client
│   └── tools/
│       ├── web_search.py     # SerpAPI
│       ├── python_repl.py    # Sandboxed Python
│       ├── email.py          # Resend + recipient validation
│       └── document_reader.py
├── api/
│   ├── index.py              # FastAPI (Vercel)
│   └── static/index.html     # Web chat UI
├── app.py                    # Streamlit UI (local)
├── public/index.html         # Static UI copy
├── tests/                    # pytest suite
├── send_test_email.py        # Resend smoke test
├── .env.example              # Template (no secrets)
├── requirements.txt
├── pyproject.toml
├── vercel.json
└── README.md
```

---

## Development

```bash
pip install -r requirements-dev.txt
ruff check agent api tests app.py
pytest -q
```

CI runs on push via `.github/workflows/ci.yml`.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Email only to one address | Using Resend test sender | Switch to `EMAIL_PROVIDER=smtp` with Gmail App Password |
| SMTP authentication failed | Wrong password | Use Google App Password, not your regular Gmail password |
| No email sent at all | Wrong agent mode | Use **3 · Full pipeline (+ email)** |
| Agent stops before email | Gemini quota or Vercel timeout | Retry; use shorter prompt or run locally |
| Document not read | Legacy `.doc` file | Save as `.docx` or PDF |
| Missing env on Vercel | Keys not set in dashboard | Add all vars in Vercel → Settings → Environment Variables |

---

## License

MIT
