from agent.context import parse_recipient_string, set_active_recipients


def test_parse_recipient_string():
    assert parse_recipient_string("a@test.com, b@test.com") == ["a@test.com", "b@test.com"]
    assert parse_recipient_string("") == []


def test_active_recipients():
    set_active_recipients(["ui@test.com"])
    from agent.context import get_active_recipients

    assert get_active_recipients() == ["ui@test.com"]
    set_active_recipients(None)
    assert get_active_recipients() is None
