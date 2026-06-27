"""Quick Resend smoke test. Run: python send_test_email.py"""

import os
import sys

import resend
from dotenv import load_dotenv
from resend.exceptions import ResendError

from agent.config import get_missing_env_keys
from agent.errors import friendly_agent_error

load_dotenv()

missing = get_missing_env_keys()
if missing:
    print(f"Missing environment variables: {', '.join(missing)}")
    sys.exit(1)

try:
    resend.api_key = os.environ["RESEND_API_KEY"]
    response = resend.Emails.send(
        {
            "from": os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev"),
            "to": os.environ["RESEND_TO_EMAIL"],
            "subject": "AI Research Agent — test email",
            "html": "<p>Your Resend setup is working. The agent can send research summaries.</p>",
        }
    )
    print(f"Email sent (id: {response['id']})")
except ResendError as exc:
    err = friendly_agent_error(exc)
    print(err)
    if err.hint:
        print(f"Hint: {err.hint}")
    sys.exit(1)
