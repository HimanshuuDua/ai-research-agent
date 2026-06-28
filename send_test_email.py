"""Quick email smoke test. Run: python send_test_email.py"""

import sys

from dotenv import load_dotenv

from agent.config import get_email_provider, get_email_recipients, get_missing_env_keys
from agent.email_delivery import deliver_email
from agent.errors import AgentServiceError, friendly_agent_error

load_dotenv()

missing = get_missing_env_keys()
if missing:
    print(f"Missing environment variables: {', '.join(missing)}")
    sys.exit(1)

provider = get_email_provider()
recipients = get_email_recipients()

try:
    result = deliver_email(
        recipients,
        "AI Research Agent — test email",
        "<p>Your email setup is working. The agent can send research summaries.</p>",
    )
    print(f"[{provider}] {result}")
except AgentServiceError as exc:
    print(exc)
    if exc.hint:
        print(f"Hint: {exc.hint}")
    sys.exit(1)
except Exception as exc:
    err = friendly_agent_error(exc)
    print(err)
    if err.hint:
        print(f"Hint: {err.hint}")
    sys.exit(1)
