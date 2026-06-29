from agent.agent import AgentStep, email_status_from_steps, suggest_next_steps


def test_suggest_after_search_only():
    steps = [AgentStep(tool="web_search", input="ev", output="results")]
    suggestions = suggest_next_steps("search_only", steps)
    labels = [s["label"] for s in suggestions]
    assert "Should I email this?" in labels
    assert "Analyze the data" in labels
    assert "Dig deeper" not in labels


def test_suggest_after_email_sent():
    steps = [
        AgentStep(tool="web_search", input="ev", output="results"),
        AgentStep(
            tool="send_email",
            input="subject",
            output="Email sent successfully to user@test.com (id: abc).",
        ),
    ]
    suggestions = suggest_next_steps("full", steps)
    labels = [s["label"] for s in suggestions]
    assert "Research another topic" in labels
    assert "Should I email this?" not in labels


def test_email_status_from_steps():
    steps = [
        AgentStep(
            tool="send_email",
            input="subject",
            output="Email sent successfully to user@test.com.",
        )
    ]
    status = email_status_from_steps(steps)
    assert status["sent"] is True
