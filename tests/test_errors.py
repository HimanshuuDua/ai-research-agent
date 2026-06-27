from google.api_core.exceptions import ResourceExhausted

from agent.errors import AgentServiceError, friendly_agent_error


def test_quota_error_message():
    err = friendly_agent_error(ResourceExhausted("429 quota exceeded"))
    assert isinstance(err, AgentServiceError)
    assert "quota" in str(err).lower()
    assert err.hint is not None


def test_invalid_api_key_message():
    err = friendly_agent_error(Exception("API key not valid"))
    assert "Invalid Google API key" in str(err)


def test_serpapi_error_message():
    err = friendly_agent_error(ValueError("Got error from SerpAPI: Invalid API key"))
    assert "Web search failed" in str(err)
