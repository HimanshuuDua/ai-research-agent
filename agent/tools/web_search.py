import os

from langchain_community.utilities import SerpAPIWrapper
from langchain_core.tools import Tool


def get_web_search_tool() -> Tool:
    """SerpAPI-powered web search — start here when building the agent."""
    search = SerpAPIWrapper(serpapi_api_key=os.environ["SERPAPI_API_KEY"])

    return Tool(
        name="web_search",
        description=(
            "Search the web for current information, news, trends, and facts. "
            "Use this first when the user asks you to research a topic."
        ),
        func=search.run,
    )
