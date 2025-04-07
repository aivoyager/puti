"""
@Author: obstacles
@Time:  2025-04-07 17:48
@Description:  
"""
from typing import Any

import faiss
from faiss import IndexIDMap
import openai
import numpy as np
import json

from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from llm.nodes import OpenAINode, LLMNode
from utils.path import root_dir


class FaissIndex(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node: LLMNode = Field(default_factory=OpenAINode, validate_default=True)
    index: IndexIDMap = Field(default=None)
    from_file: Path = Field(default=root_dir() / 'data' / 'test.json', validate_default=True)
    to_file: Path = Field(default=root_dir() / 'db' / 'faiss.index', validate_default=True)

    def _get_embeddings(self, texts) -> np.array:
        response = self.node.cli.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return np.array([e.embedding for e in response.data]).astype("float32")

    def model_post_init(self, __context: Any) -> None:
        with open(str(self.from_file), 'r', encoding='utf-8') as f:
            data = json.load(f)

        texts = [item['text'] for item in data]
        ids = [int(item['id']) for item in data]  # FAISS 要求 ID 是 int64

        vectors = self._get_embeddings(texts)

        d = vectors.shape[1]
        index = faiss.IndexIDMap(faiss.IndexFlatL2(d))
        index.add_with_ids(vectors, np.array(ids, dtype=np.int64))

        faiss.write_index(index, str(self.to_file))
