"""
@Author: obstacles
@Time:  2025-04-07 17:48
@Description:  
"""
from typing import Any, Tuple

import faiss
from faiss import IndexIDMap
import openai
import numpy as np
import json
import pandas as pd

from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from llm.nodes import OpenAINode, LLMNode
from utils.path import root_dir
from conf.llm_config import LLMConfig, OpenaiConfig


class FaissIndex(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node: LLMNode = Field(default_factory=OpenAINode, validate_default=True)
    index: IndexIDMap = Field(default=None)
    from_file: Path = Field(default=root_dir() / 'data' / 'test.json', validate_default=True)
    to_file: Path = Field(default=root_dir() / 'db' / 'test.index', validate_default=True)
    conf: LLMConfig = Field(default_factory=OpenaiConfig, validate_default=True)

    def get_embeddings(self, texts) -> np.array:
        response = self.node.cli.embeddings.create(
            model=self.conf.EMBEDDING_MODEL,
            input=texts
        )
        return np.array([e.embedding for e in response.data]).astype("float32")

    def get_origin_by_ids(self, ids: np.array):
        with open(str(self.from_file), 'r') as f:
            origin = json.load(f)
        df = pd.DataFrame(origin)
        origin = df.loc[df['id'].isin(ids[0]), 'text'].tolist()
        return origin

    def search(self, query) -> Tuple:
        embeddings = self.get_embeddings(query)
        distance, indices = self.index.search(embeddings, self.conf.FAISS_SEARCH_TOP_K)
        origin = self.get_origin_by_ids(indices)
        return distance, origin

    def model_post_init(self, __context: Any) -> None:
        if not self.to_file.exists():
            with open(str(self.from_file), 'r', encoding='utf-8') as f:
                data = json.load(f)

            texts = [item['text'] for item in data]
            ids = [int(item['id']) for item in data]  # FAISS 要求 ID 是 int64

            vectors = self.get_embeddings(texts)

            d = vectors.shape[1]
            index = faiss.IndexIDMap(faiss.IndexFlatL2(d))
            index.add_with_ids(vectors, np.array(ids, dtype=np.int64))

            self.index = index
            faiss.write_index(index, str(self.to_file))
        else:
            self.index = faiss.read_index(str(self.to_file))
