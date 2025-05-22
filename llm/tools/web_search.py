"""
@Author: obstacles
@Time:  2025-05-19 10:57
@Description:  
"""
import re
import asyncio
import random
import requests
import time
import numpy as np

from sklearn.metrics.pairwise import cosine_similarity
from typing import List

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from googlesearch import search as g_search
from pydantic import BaseModel, ConfigDict, Field
# from llama_index.core import VectorStoreIndex, Document

from core.resp import Response, ToolResponse
from llm.nodes import LLMNode, OpenAINode
from llm.tools import BaseTool, ToolArgs
from logs import logger_factory
from utils.path import root_dir
# from llama_index.core import SimpleDirectoryReader, Document, VectorStoreIndex

lgr = logger_factory.llm


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
    chunk_storage: List[str] = []

    def split_into_chunks(self, text: str, max_length: int = 500, chunk_overlap: float = 0.1) -> List[str]:
        sentences = re.findall(r'[^。！？．!?.,]+[。！？．!?.,]?', text)
        chunks = []
        current_chunk = []
        current_length = 0
        overlap_size = int(max_length * chunk_overlap)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            # 首个chunk不进行分块
            if current_length + len(sentence) > max_length and current_chunk:
                chunks.append(' '.join(current_chunk))
                # 保留重叠部分 current[N:] 最后n个句子作为重叠内容 ，保留上一轮的N个句子
                current_chunk = current_chunk[
                                -int(
                                    # 保留多少个句子才能达到overlap_size字符数的重叠，为粗略估计，假设所有句子长度和最后一句差不多
                                    # overlap_size / len(current_chunk[-1])
                                    overlap_size / (
                                        len(current_chunk[-1]) if current_chunk else 1
                                    )
                                ):
                ]
                current_length = sum(len(s) for s in current_chunk)

            current_chunk.append(sentence)
            current_length += len(sentence)

        if current_chunk:
            chunks.append(' '.join(current_chunk))

            self.chunk_storage.extend(chunks)
        return chunks

    async def fetch_text_from_url(self, url) -> ToolResponse:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for script in soup(['script', 'style']):
                    script.decompose()

                text = soup.get_text(separator='\n')
                chunks = self.split_into_chunks(text, max_length=200, chunk_overlap=0.01)
                return ToolResponse.success(data=chunks)
            else:
                return ToolResponse.fail(msg=f"Failed to fetch text from URL: {url}. Status code: {resp.status_code}")
        except Exception as e:
            return ToolResponse.fail(msg=f"Failed to fetch text from URL: {url}. Error: {str(e)}")

    @staticmethod
    async def get_embeddings(llm, contents: list):
        return await asyncio.gather(*[llm.embedding(text=content) for content in contents])

    @staticmethod
    def compute_similarity(embeddings, query_embedding, top_k=3):

        emb_matrix = np.array(embeddings)
        query_vec = np.array(query_embedding).reshape(1, -1)
        similarities = cosine_similarity(emb_matrix, query_vec).flatten()
        top_k = min(top_k, len(similarities))
        top_indices = similarities.argsort()[::-1][:top_k]
        return top_indices, similarities

    async def embedding_similarity_search(self, llm: OpenAINode, query: str, num_results: int = 10, *args, **kwargs) -> ToolResponse:
        engine_name = kwargs.get('search_engine', 'google')
        search_engine = self._search_engine.get(engine_name)
        fetch_resp = await self.fetch_urls_and_contents(search_engine, query, num_results)
        if not fetch_resp.is_success():
            return fetch_resp

        all_chunks = [chunk for content in fetch_resp.data for chunk in content]
        embeddings = await self.get_embeddings(llm, all_chunks)
        query_embedding = await llm.embedding(text=query)
        top_indices, _ = self.compute_similarity(embeddings, query_embedding, top_k=3)
        relevant_contents = [all_chunks[i] for i in top_indices]
        return ToolResponse(data=relevant_contents)

    async def run(
            self,
            llm: OpenAINode,
            query: str,
            num_results: int = 10,
            *args,
            **kwargs
    ) -> ToolResponse:
        self.chunk_storage.clear()
        st = time.time()
        loop = asyncio.get_event_loop()
        search_resp = await loop.run_in_executor(
            None,
            lambda: self._search_engine['google'].search(query, num_results=num_results)
        )
        urls = search_resp[:num_results]

        responses = await asyncio.gather(*[self.fetch_text_from_url(url) for url in urls])

        total_content = []
        for url, resp in zip(urls, responses):
            if resp.is_success():
                total_content.append(resp.data)
            else:
                lgr.warning(f"Failed to fetch content from URL: {url}. Error: {resp.msg}")
        if not total_content:
            return ToolResponse.fail(msg=f"Failed to fetch content from URL: {search_resp}")
        lgr.debug(f'fetch_urls_and_contents cost: {time.time()-st}')
        return ToolResponse.success(data=total_content)
