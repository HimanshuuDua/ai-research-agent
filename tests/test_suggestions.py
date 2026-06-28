from agent.agent import AgentStep, suggest_next_steps


def test_suggest_after_search_only():
    steps = [AgentStep(tool="web_search", input="ev", output="results")]
    suggestions = suggest_next_steps("search_only", steps)
    labels = [s["label"] for s in suggestions]
    assert "Analyze with Python" in labels
    assert "Email me a summary" in labels


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
