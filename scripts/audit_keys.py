"""Audit Gemini and email rotation config without printing secrets."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.config import get_email_provider
from agent.email_delivery import get_email_pool_size
from agent.key_pool import get_brevo_api_keys, get_google_api_keys, get_resend_api_keys, get_smtp_accounts, _split_keys


def load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def apply_env(data: dict[str, str]) -> None:
    os.environ.clear()
    for key, value in data.items():
        os.environ[key] = value


def audit_gemini(data: dict[str, str]) -> dict:
    apply_env(data)
    keys = get_google_api_keys()
    return {
        "gemini_key_count": len(keys),
        "gemini_rotation_ready": len(keys) > 1,
    }


def audit_email(data: dict[str, str]) -> dict:
    apply_env(data)
    provider = get_email_provider()
    pool = get_email_pool_size()
    smtp_accounts = get_smtp_accounts()
    return {
        "email_provider": provider,
        "email_account_count": pool,
        "email_rotation_ready": pool > 1,
        "smtp_accounts": len(smtp_accounts),
        "brevo_keys": len(get_brevo_api_keys()),
        "resend_keys": len(get_resend_api_keys()),
    }


def audit_file(path: Path) -> dict:
    data = load_env_file(path)
    if not data:
        return {"file": str(path), "exists": False}
    return {
        "file": str(path),
        "exists": True,
        **audit_gemini(data),
        **audit_email(data),
    }


def main() -> None:
    targets = [ROOT / ".env", ROOT / ".env.vercel.prod"]
    if len(sys.argv) > 1:
        targets = [Path(p) for p in sys.argv[1:]]
    for path in targets:
        print(audit_file(path))


if __name__ == "__main__":
    main()
