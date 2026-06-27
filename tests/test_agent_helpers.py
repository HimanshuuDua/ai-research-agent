from langchain_core.messages import AIMessage, HumanMessage

from agent.agent import AgentStep, _normalize_chat_history, _steps_from_intermediate


class FakeAction:
    def __init__(self, tool, tool_input):
        self.tool = tool
        self.tool_input = tool_input


def test_normalize_chat_history_from_dicts():
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    normalized = _normalize_chat_history(history)
    assert isinstance(normalized[0], HumanMessage)
    assert isinstance(normalized[1], AIMessage)


def test_steps_from_intermediate():
    steps = _steps_from_intermediate(
        [
            (FakeAction("web_search", "ev trends"), "result text"),
            (FakeAction("python_repl", {"query": "print(1)"}), "1"),
        ]
    )
    assert len(steps) == 2
    assert isinstance(steps[0], AgentStep)
    assert steps[0].tool == "web_search"
