"""
@Author: obstacles
@Time:  2025-03-10 17:22
@Description:  
"""
import asyncio
import threading

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Iterable, Any
import faiss
import numpy as np

from pathlib import Path
from puti.llm.messages import Message, AssistantMessage, UserMessage
from puti.llm.nodes import LLMNode, OpenAINode
from puti.constant.llm import RoleType
from puti.constant.base import Pathh
from puti.utils.files import save_texts_to_file, load_texts_from_file


class Memory(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # Short-term memory for exact conversation history
    storage: List[Message] = Field(default_factory=list)

    # Long-term memory using Faiss
    llm: Optional[LLMNode] = Field(default_factory=OpenAINode, exclude=True)
    top_k: int = 3
    index: Optional[faiss.Index] = Field(None, exclude=True, validate_default=True)
    texts: List[str] = Field(default_factory=list, exclude=True)
    _embedding_dim: Optional[int] = None

    def to_dict(self, ample: bool = False):
        """ Returns the short-term memory as a list of dictionaries. """
        memories = self.get()
        resp = []
        for memory in memories:
            item = {'role': memory.role.val, 'content': memory.content if not ample else memory.ample_content}
            resp.append(item)
        return resp

    def get(self, k: int = 0) -> List[Message]:
        """ Gets the last k messages from short-term memory. 0 for all. """
        if k == 0:
            return self.storage
        return self.storage[-k:]

    def get_newest(self) -> Optional[Message]:
        """ Gets the most recent message from short-term memory. """
        return self.storage[-1] if self.storage else None

    async def add_one(self, message: Message, *args, **kwargs):
        """ Adds a message to both short-term and long-term memory. """
        self.storage.append(message)

        # Also add to long-term vector memory
        if self.llm:
            if message.is_user_message():
                # Image message won't be embedded cause it store in `message.non_standard`
                content_to_embed = f"User asked: {message.content}"
            elif message.is_assistant_message():
                if kwargs.get('role'):
                    content_to_embed = f"{kwargs['role']} responded: {message.content}"
                else:
                    content_to_embed = f"You responded: {message.content}"
            else:
                content_to_embed = ''
            if content_to_embed and content_to_embed not in self.texts:
                await self._add_to_vector_store(content_to_embed)

    async def add_batch(self, messages: Iterable[Message]):
        for msg in messages:
            await self.add_one(msg)

    # --- Faiss-based Long-Term Memory Methods ---

    async def _initialize_index(self):
        if self.index is None:
            index_file_path = Path(Pathh.INDEX_FILE.val)
            texts_file_path = Path(Pathh.INDEX_TEXT.val)

            if index_file_path.exists():
                self.index = faiss.read_index(str(index_file_path))
                self.texts = load_texts_from_file(texts_file_path)
            else:
                if not self.llm:
                    raise ValueError("LLMNode must be provided for vector memory operations.")
                dim = await self.llm.get_embedding_dim()
                self.index = faiss.IndexFlatL2(dim)
                # Ensure the directory exists before saving
                index_file_path.parent.mkdir(parents=True, exist_ok=True)
                faiss.write_index(self.index, str(index_file_path))
                save_texts_to_file(self.texts, texts_file_path)

    async def _add_to_vector_store(self, text: str):
        embedding = await self.llm.embedding(text=text)
        vector = np.array([embedding], dtype="float32")
        self.index.add(vector)
        self.texts.append(text)

        # Save index and texts after adding new data
        faiss.write_index(self.index, Pathh.INDEX_FILE.val)
        save_texts_to_file(self.texts, Path(Pathh.INDEX_TEXT.val))

    async def search(self, query: str, top_k: Optional[int] = None) -> List[str]:
        """ Searches long-term memory for texts relevant to the query. """
        if self.index is None or self.index.ntotal == 0 or not self.llm:
            return []

        num_to_retrieve = top_k if top_k is not None else self.top_k
        num_to_retrieve = min(num_to_retrieve, self.index.ntotal)

        if num_to_retrieve == 0:
            return []

        query_embedding = await self.llm.embedding(text=query)  # TODO: Cache same query embedding
        vector = np.array([query_embedding], dtype="float32")
        distances, indices = self.index.search(vector, k=num_to_retrieve)

        # Filter out results that are too similar to the query (i.e., the query itself)
        # and only include results with a distance less than 0.5 for high relevance.
        results = []
        if len(indices) > 0:
            for i, dist in zip(indices[0], distances[0]):
                # A very small distance (e.g., < 1e-5) indicates an exact match to the query.
                # A distance > 0.5 indicates low semantic relevance. [0 - 2 distance]
                if 1e-5 < dist < 0.5:
                    results.append(self.texts[i])
        return results

    def clear(self):
        """ Clears both short-term and long-term memory. """
        self.storage.clear()
        self.index = None
        self.texts.clear()
        index_file_path = Path(Pathh.INDEX_FILE.val)
        texts_file_path = index_file_path.with_suffix('.txt')
        if index_file_path.exists():
            index_file_path.unlink()
        if texts_file_path.exists():
            texts_file_path.unlink()

    def model_post_init(self, __context: Any) -> None:
        if not self.index:
            def _run_async_init():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(self._initialize_index())
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(None)

            thread = threading.Thread(target=_run_async_init)
            thread.start()
            thread.join()  # 阻塞当前线程直到初始化完成


