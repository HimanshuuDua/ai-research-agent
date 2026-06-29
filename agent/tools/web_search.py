import os

from langchain_community.utilities import SerpAPIWrapper
from langchain_core.tools import Tool

from agent.errors import friendly_agent_error


MAX_SEARCH_CHARS = 3500


def _search(query: str) -> str:
    try:
        search = SerpAPIWrapper(
            serpapi_api_key=os.environ["SERPAPI_API_KEY"],
            params={"num": 5},
        )
        result = search.run(query)
        if len(result) > MAX_SEARCH_CHARS:
            return result[:MAX_SEARCH_CHARS] + "\n\n[Search results truncated for speed.]"
        return result
    except Exception as exc:
        raise friendly_agent_error(exc) from exc


def get_web_search_tool() -> Tool:
    return Tool(
        name="web_search",
        description=(
            "Search the web for current information, news, trends, and facts. "
            "Use this first when the user asks you to research a topic."
        ),
        func=_search,
    )
