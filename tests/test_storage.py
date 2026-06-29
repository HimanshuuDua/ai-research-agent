from agent.storage import append_message, get_session_messages, init_db, session_key_from_request


def test_storage_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "test.db"))
    init_db()
    key = session_key_from_request("203.0.113.10", "test-agent")
    append_message(key, key[:16], "user", "Hello")
    append_message(key, key[:16], "assistant", "Hi there", model_used="gemini")
    messages = get_session_messages(key)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["content"] == "Hi there"
