"""
@Author: obstacles
@Time:  2025-05-19 10:57
@Description:  
"""
import asyncio
import requests
import time
import random

from utils.path import root_dir
from abc import ABC, abstractmethod
from llm.tools import BaseTool, ToolArgs
from pydantic import ConfigDict, Field, BaseModel
from googlesearch import search as g_search
from core.resp import ToolResponse, Response
from typing import List
from bs4 import BeautifulSoup


class WebSearchEngine(BaseModel, ABC):

    @abstractmethod
    def search(self, query, num_results: int = 10, *args, **kwargs):
        pass


class GoogleSearchEngine(WebSearchEngine):

    def search(self, query, num_results: int = 10, *args, **kwargs):
        gen_resp = g_search(query, num=num_results, *args, **kwargs)
        count = 0
        resp = []
        while count < num_results:
            try:
                url = next(gen_resp)
                resp.append(url)
                count += 1
            except StopIteration:
                break
        return resp


class WebSearchArgs(ToolArgs, ABC):
    query: str = Field(..., description="The search query to submit to the search engine.")
    num_results: int = Field(default=10, description="The number of search results to return. Default is 10.")


class WebSearch(BaseTool, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'web_search'
    desc: str = """Perform a web search and return a list of relevant links.
    This function attempts to use the primary search engine API to get up-to-date results.
    If an error occurs, it falls back to an alternative search engine."""
    args: WebSearchArgs = None

    _search_engine: dict[str, WebSearchEngine] = {
        'google': GoogleSearchEngine()
    }

    @staticmethod
    def fetch_text_from_url(url) -> ToolResponse:
        try:
            # time.sleep(random.uniform(1, 3))
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for script in soup(['script', 'style']):
                    script.decompose()

                text = soup.get_text(separator='\n')
                lines = [line.strip() for line in text.splitlines()]
                clean_text = ''.join(line for line in lines if line)
                return ToolResponse.success(data='Searched context: ' + clean_text)
            else:
                return ToolResponse.fail(msg=f"Failed to fetch text from URL: {url}. Status code: {resp.status_code}")
        except Exception as e:
            return ToolResponse.fail(msg=f"Failed to fetch text from URL: {url}. Error: {str(e)}")

    async def run(self, query: str, num_results: int = 10, *args, **kwargs) -> ToolResponse:
        engine_name = kwargs.get('search_engine', 'google')
        search_engine = self._search_engine.get(engine_name)
        loop = asyncio.get_event_loop()
        search_resp = await loop.run_in_executor(
            None,
            lambda: search_engine.search(query, num_results=num_results)
        )
        total_content = []
        for url in search_resp:
            resp = await self.fetch_text_from_url(url)

            if resp.is_success():
                return resp
        
        return search_resp
