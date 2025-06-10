"""
@Author: obstacles
@Time:  2025-03-10 17:20
@Description:  
"""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict, create_model, model_validator, PrivateAttr, SerializeAsAny, field_validator
from typing import Optional, List, Iterable, Literal, Set
from typing import Dict, Tuple, Type, Any, Union
from uuid import uuid4
from puti.llm.messages import Message
from logs import logger_factory
from collections import defaultdict
from typing import TYPE_CHECKING
from puti.constant.llm import MessageTag
from capture import Capture

import asyncio

if TYPE_CHECKING:
    from puti.llm.roles import Role
from puti.llm.messages import Message

lgr = logger_factory.llm


class Env(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), validate_default=True, description='Unique code of messages')
    name: str = Field(default='public area', description='Env name')
    desc: str = Field(default='maybe there are other agents out there', description='Description of env')
    messages: List[Dict] = None
    # TODO: children envs and parent env
    children_envs: List['Env'] = None
    parent_env: 'Env' = None
    members: Set['Role'] = set()
    members_addr: Dict['Role', set[str]] = Field(default_factory=lambda: defaultdict(set), description='key is role name, value is role address')
    history: List[Message] = []
    cp: SerializeAsAny[Capture] = Field(default_factory=Capture, validate_default=True, description='Capture exception')

    @property
    def env_prompt(self):
        prompt = f'You are in {self.name}({self.desc}) now.'
        return prompt

    def add_roles(self, roles: Iterable['Role']):
        for role in roles:
            role.rc.env = self
            self.members_addr.update({role: role.address})
            self.members.add(role)

    def publish_message(self, msg: Message):
        """ Publish message to all members exclude myself """
        lgr.debug(f'Publishing message: {msg}')
        has_receiver = False
        for role, addr in self.members_addr.items():
            if ((MessageTag.ALL.val in msg.receiver or msg.receiver & role.address)
                    and msg.sender != role.name):
                role.rc.buffer.put_one_msg(msg)
                has_receiver = True
        if not has_receiver:
            lgr.warning(f'No receiver for message: {msg}')
        self.history.append(msg)

    async def run(self, run_round: int = 5):
        n = 0
        while n < run_round:
            futures = []
            for member in self.members:
                future = member.run()
                futures.append(future)
            resp = await asyncio.gather(*futures)
            n += 1
            lgr.debug(f'env [{self.name}] run round: [{n + 1}/{run_round}]; members: {self.members}')
            print(f'round: {n} resp: {resp}')

    @property
    def is_idle(self):
        for member in self.members:
            if not member.is_idle:
                return False
        return True

    @classmethod
    def model_rebuild(cls, **kwargs):
        from puti.llm.roles import Role  # noqa: F401
        super().model_rebuild(**kwargs)


