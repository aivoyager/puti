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
from llm.messages import Message
from logs import logger_factory
from collections import defaultdict
from typing import TYPE_CHECKING
from constant.llm import MessageRouter
if TYPE_CHECKING:
    from llm.roles import Role
import asyncio

lgr = logger_factory.llm


class Env(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), validate_default=True, description='Unique code of messages')
    name: str = Field(default='', description='Env name')
    desc: str = Field(default='', description='Description of env')
    messages: List[Dict] = None
    # TODO: children envs and parent env
    children_envs: List['Env'] = None
    parent_env: 'Env' = None
    members: Set['Role'] = set()
    members_addr: Dict['Role', set[str]] = Field(default_factory=lambda: defaultdict(set), description='key is role name, value is role address')
    history: str = ''

    def add_roles(self, roles: Iterable['Role']):
        for role in roles:
            role.rc.env = self
            self.members_addr.update({role: role.address})
            self.members.add(role)

    def publish_message(self, msg: Message):
        lgr.debug(f'Publishing message: {msg}')
        has_receiver = False
        for role, addr in self.members_addr.items():
            if MessageRouter.ALL.val in msg.receiver or msg.receiver | role.address:
                role.rc.buffer.put_one_msg(msg)
                has_receiver = True
        if not has_receiver:
            lgr.warning(f'No receiver for message: {msg}')
        self.history += f'{msg}\n'

    async def run(self):
        futures = []
        for member in self.members:
            future = member.run()
            futures.append(future)
        await asyncio.gather(*futures)
        print('')

    @property
    def is_idle(self):
        for member in self.members:
            if not member.is_idle:
                return False
        return True
