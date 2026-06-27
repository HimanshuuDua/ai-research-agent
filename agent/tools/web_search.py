import os

from langchain_community.utilities import SerpAPIWrapper
from langchain_core.tools import Tool

from agent.errors import friendly_agent_error


def _search(query: str) -> str:
    try:
        search = SerpAPIWrapper(serpapi_api_key=os.environ["SERPAPI_API_KEY"])
        return search.run(query)
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
