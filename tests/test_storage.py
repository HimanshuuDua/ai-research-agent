from agent.storage import (
    append_message,
    get_session_messages,
    init_db,
    session_key_from_request,
    use_supabase,
)


def test_storage_roundtrip(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "test.db"))
    assert use_supabase() is False
    init_db()
    key = session_key_from_request("203.0.113.10", "test-agent")
    append_message(key, key[:16], "user", "Hello")
    append_message(key, key[:16], "assistant", "Hi there", model_used="gemini")
    messages = get_session_messages(key)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["content"] == "Hi there"


def test_use_supabase_detects_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
    assert use_supabase() is True
