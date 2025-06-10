"""
@Author: obstacles
@Time:  2025-03-10 17:22
@Description:  
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Iterable
import faiss
import numpy as np

from puti.llm.messages import Message, AssistantMessage, UserMessage
from puti.llm.nodes import LLMNode
from puti.constant.llm import RoleType


class Memory(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # Short-term memory for exact conversation history
    storage: List[Message] = Field(default_factory=list)

    # Long-term memory using Faiss
    llm: Optional[LLMNode] = Field(None, exclude=True)
    top_k: int = 3
    index: Optional[faiss.Index] = Field(None, exclude=True)
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

    async def add_one(self, message: Message):
        """ Adds a message to both short-term and long-term memory. """
        self.storage.append(message)

        # Also add to long-term vector memory
        if self.llm:
            if message.is_user_message():
                content_to_embed = f"User asked: {message.content}"
            elif message.is_assistant_message():
                content_to_embed = f"You responded: {message.content}"
            else:
                content_to_embed = ''
            if content_to_embed:
                await self._add_to_vector_store(content_to_embed)

    async def add_batch(self, messages: Iterable[Message]):
        for msg in messages:
            await self.add_one(msg)

    # --- Faiss-based Long-Term Memory Methods ---

    async def _initialize_index(self):
        if self.index is None:
            if not self.llm:
                raise ValueError("LLMNode must be provided for vector memory operations.")
            dim = await self.llm.get_embedding_dim()
            self.index = faiss.IndexFlatL2(dim)

    async def _add_to_vector_store(self, text: str):
        if self.index is None:
            await self._initialize_index()

        embedding = await self.llm.embedding(text=text)
        vector = np.array([embedding], dtype="float32")
        self.index.add(vector)
        self.texts.append(text)

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
        results = []
        if len(indices) > 0:
            for i, dist in zip(indices[0], distances[0]):
                # A very small distance indicates an exact or near-exact match.
                # This is likely the query itself that was just added to memory.
                # We should skip it to avoid redundancy.
                if dist > 1e-5:  # Using a small epsilon for floating point comparison
                    results.append(self.texts[i])
        return results

    def clear(self):
        """ Clears both short-term and long-term memory. """
        self.storage.clear()
        self.index = None
        self.texts.clear()
