"""Audit Gemini key pool config without printing secrets."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.key_pool import get_google_api_keys, _split_keys


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


def audit_file(path: Path) -> dict:
    data = load_env_file(path)
    os.environ.clear()
    if data.get("GOOGLE_API_KEYS"):
        os.environ["GOOGLE_API_KEYS"] = data["GOOGLE_API_KEYS"]
    if data.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = data["GOOGLE_API_KEY"]
    single = data.get("GOOGLE_API_KEY", "")
    multi = data.get("GOOGLE_API_KEYS", "")
    keys = get_google_api_keys()
    return {
        "file": str(path),
        "has_GOOGLE_API_KEYS": bool(multi),
        "has_GOOGLE_API_KEY": bool(single),
        "GOOGLE_API_KEY_len": len(single),
        "GOOGLE_API_KEY_commas": single.count(","),
        "GOOGLE_API_KEYS_count": len(_split_keys(multi)) if multi else 0,
        "pool_count": len(keys),
        "pool_unique": len(set(keys)),
        "rotation_ready": len(keys) > 1,
    }


def main() -> None:
    targets = [ROOT / ".env", ROOT / ".env.vercel.prod"]
    if len(sys.argv) > 1:
        targets = [Path(p) for p in sys.argv[1:]]
    for path in targets:
        print(audit_file(path))


if __name__ == "__main__":
    main()
