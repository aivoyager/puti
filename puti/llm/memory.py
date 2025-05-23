"""
@Author: obstacles
@Time:  2025-03-10 17:22
@Description:  
"""
from pydantic import BaseModel, Field, ConfigDict, create_model, model_validator, PrivateAttr, SerializeAsAny, field_validator
from typing import Optional, List, Iterable, Literal, Union
from llm.messages import Message
from llm.roles import RoleType


class Memory(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    storage: List[SerializeAsAny[Message]] = []

    def to_dict(self, ample: bool = False):
        """  """
        memories = self.get()
        resp = []
        for memory in memories:
            item = {'role': memory.role.val, 'content': memory.content if not ample else memory.ample_content}
            resp.append(item)
        return resp

    def get(self, k=0) -> List[Message]:
        """ top k , 0 for all"""
        return self.storage[-k:]

    def add_one(self, message: Message):
        self.storage.append(message)

    def add_batch(self, messages: Iterable[Message]):
        for msg in messages:
            self.add_one(msg)
