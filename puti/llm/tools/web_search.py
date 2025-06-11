"""
@Author: obstacles
@Time:  2025-05-19 10:57
@Description:  `llama_index` not support python 3.12
"""
import re
import asyncio
import random
import requests
import time
import numpy as np
import itertools
import tiktoken
import urllib
import codecs

from sklearn.metrics.pairwise import cosine_similarity
from typing import List
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from googlesearch import search as g_search
from pydantic import BaseModel, ConfigDict, Field
# from llama_index.core import VectorStoreIndex, Document
from puti.core.resp import Response, ToolResponse
from puti.llm.nodes import LLMNode, OpenAINode
from puti.llm.tools import BaseTool, ToolArgs
from puti.logs import logger_factory
from puti.utils.path import root_dir
# from llama_index.core import SimpleDirectoryReader, Document, VectorStoreIndex

lgr = logger_factory.llm


class WebSearchEngine(BaseModel, ABC):

    @abstractmethod
    def search(self, query, retrieval_url_count, *args, **kwargs):
        pass


class GoogleSearchEngine(WebSearchEngine):

    def search(self, query, retrieval_url_count, *args, **kwargs):
        # `num` This argument didn't work
        gen_resp = g_search(query, num_results=retrieval_url_count, region='US', *args, **kwargs)
        count = 0
        resp = []
        while count < retrieval_url_count:
            try:
                url = next(gen_resp)
                resp.append(url)
                count += 1
            except StopIteration:
                break
        return resp


class WebSearchArgs(ToolArgs, ABC):
    query: str = Field(..., description="The search query text.")
    num_results: int = Field(default=3, description="The number of search results to return. Default is 3.")


class WebSearch(BaseTool, ABC):

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'web_search'
    desc: str = (
        "Performs a web search to find real-time, up-to-date information on the internet. "
        "Use this tool when you need current information beyond your knowledge cut-off date, such as today's news, "
        "recent events, or the latest developments on a topic. It is also useful for finding specific facts, "
        "articles, or general information that is not part of your internal knowledge."
    )
    args: WebSearchArgs = None

    _search_engine: dict[str, WebSearchEngine] = {
        'google': GoogleSearchEngine()
    }
    chunk_storage: List[str] = []

    def split_into_chunks(self, text: str, max_chars: int = 5000, overlap_sentences_count: int = 1) -> List[str]:
        sentences_text_list = re.findall(r'[^。！？．!?.]+[。！？．!?.]?', text)
        sentences_text_list = [s.strip() for s in sentences_text_list if s.strip()]
        if not sentences_text_list:
            return []
        chunk_storage = []
        current_chunk = []
        current_chunk_chars = 0
        enc = tiktoken.get_encoding("cl100k_base")
        for sentence in sentences_text_list:
            sentence_text = sentence.strip()
            if not sentence_text:
                continue

            while len(sentence_text) > max_chars:
                overlap_len = max_chars // 5 if overlap_sentences_count > 0 else 0
                chunk_storage.append(sentence_text[:max_chars])
                print(f"[debug] forced split chunk chars={len(sentence_text[:max_chars])} tokens={len(enc.encode(sentence_text[:max_chars]))}")
                sentence_text = sentence_text[max_chars - overlap_len:]

            if current_chunk:
                join_len = len(''.join(current_chunk)) + len(sentence_text)
            else:
                join_len = len(sentence_text)

            if join_len > max_chars:
                chunk = ''.join(current_chunk)
                # lgr.debug(f"chunk chars={len(chunk)} tokens={len(enc.encode(chunk))}")
                chunk_storage.append(chunk)
                if overlap_sentences_count > 0 and len(current_chunk) > 0:
                    overlap = current_chunk[-overlap_sentences_count:] if len(current_chunk) >= overlap_sentences_count else current_chunk
                    # don't add overlap if it exceeds max_chars
                    if len(''.join(current_chunk)) + len(sentence_text) > max_chars:
                        current_chunk = []
                    else:
                        current_chunk = overlap.copy()
                else:
                    current_chunk = []
                current_chunk_chars = len(''.join(current_chunk))
            current_chunk.append(sentence_text)
            current_chunk_chars = len(''.join(current_chunk))
        if current_chunk:
            chunk = ''.join(current_chunk)
            # lgr.debug(f"chunk chars={len(chunk)} tokens={len(enc.encode(chunk))}")
            chunk_storage.append(chunk)
        self.chunk_storage.extend(chunk_storage)
        return chunk_storage

    async def fetch_text_from_url(self, url) -> ToolResponse:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for script in soup(['script', 'style']):
                    script.decompose()

                try:
                    text = soup.get_text(separator='\n').encode('latin1').decode('utf-8')
                except UnicodeEncodeError:
                    text = soup.get_text()
                text = re.sub(r'\t+', '\t', text)  # Replace multiple tabs with a single tab
                text = re.sub(r'\n+', ' ', text).strip()  # Replace multiple newlines with a single space and strip
                # Further clean up multiple spaces that might have resulted from replacements
                text = re.sub(r'\s+', ' ', text)
                chunks = self.split_into_chunks(text, max_chars=5000, overlap_sentences_count=1)
                return ToolResponse.success(data=chunks)
            else:
                return ToolResponse.fail(msg=f"Failed to fetch text from URL: {url}. Status code: {resp.status_code}")
        except Exception as e:
            return ToolResponse.fail(msg=f"Failed to fetch text from URL: {url}. Error: {str(e)}")

    @staticmethod
    def compute_similarity(embeddings, query_embedding, top_k=3):

        emb_matrix = np.array(embeddings)
        query_vec = np.array(query_embedding).reshape(1, -1)
        similarities = cosine_similarity(emb_matrix, query_vec).flatten()
        top_k = min(top_k, len(similarities))
        top_indices = similarities.argsort()[::-1][:top_k]
        return top_indices, similarities

    async def run(
            self,
            llm: OpenAINode,
            query: str,
            num_results: int = 3,
            *args,
            **kwargs
    ) -> ToolResponse:
        lgr.debug(f'{self.name} using...')

        retrieval_url_count = num_results * 2

        self.chunk_storage.clear()
        st = time.time()
        loop = asyncio.get_event_loop()
        search_resp = await loop.run_in_executor(
            None,
            lambda: self._search_engine['google'].search(query, retrieval_url_count=retrieval_url_count)
        )
        # lgr.debug(f'google web search started with `{query}`.')
        urls = search_resp[:num_results]

        responses = await asyncio.gather(*[self.fetch_text_from_url(url) for url in urls])
        # lgr.debug(f'fetch text from urls done. cost time: {time.time() - st}.')

        total_content = []
        for url, resp in zip(urls, responses):
            if resp.is_success():
                if len(resp.data) > 100:  # we think this is not a valid content
                    continue
                total_content.append(resp.data)
            else:
                # lgr.warning(f"Failed to fetch content from URL: {url}. Error: {resp.msg}")
                pass
        total_content = list(itertools.chain.from_iterable(total_content))
        if not total_content:
            return ToolResponse.fail(msg=f"Failed to fetch content from URL: {search_resp}")

        # TODO: embeddings cost
        embeddings = await asyncio.gather(*[llm.embedding(text=content) for content in total_content])
        query_embedding = await llm.embedding(text=query)
        # lgr.debug(f'embeddings done. cost time: {time.time() - st}.')

        top_indices, _ = self.compute_similarity(embeddings, query_embedding, top_k=num_results)

        selected = np.array(total_content)[top_indices].astype(str)
        prefix = np.arange(1, len(selected) + 1).astype(str)
        numbered_selected = np.char.add(prefix, '. ')
        numbered_selected = np.char.add(numbered_selected, selected)
        final = {'searched_result_on_google': '\n\n'.join(numbered_selected)}
        # lgr.debug(f'google web search done. {num_results} founded. cost time: {time.time() - st}.')
        return ToolResponse.success(data=final)
