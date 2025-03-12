"""
@Author: obstacles
@Time:  2025-03-10 17:15
@Description:  
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Iterable, Literal
from constant.llm import RoleType
from typing import Dict, Tuple, Type, Any, Union
from datetime import datetime
from uuid import uuid4
from constant.llm import MessageRouter
from utils.common import any_to_str, import_class
from llm.actions import Action


class Message(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # if design in role will loop import
    cause_by: str = Field(default='', description='message initiator Action str', validate_default=True)
    sender: str = Field(default='', validate_default=True, description='Sender role name')
    receiver: set['str'] = Field(default={MessageRouter.ALL.val}, validate_default=True, description='Receiver role name')
    reply_to: str = Field(default='', description='Message id reply to')
    id: str = Field(default_factory=lambda: str(uuid4()), description='Unique code of messages')
    content: str = ''
    instruct_content: Optional[BaseModel] = Field(default=None, validate_default=True)
    role: RoleType = Field(default=RoleType.USER, validate_default=True)
    attachment_urls: List[str] = Field(default=[], validate_default=True, description='URLs of attachments for multi modal')
    created_time: datetime = Field(default=datetime.now(), validate_default=True)

    @field_validator('cause_by', mode='before')
    @classmethod
    def check_cause_by(cls, cause_by: Any):
        s = any_to_str(cause_by if cause_by else import_class('UserRequirement', 'llm.actions'))
        return s

    @classmethod
    def from_messages(cls, messages: List[dict]) -> List["Message"]:

        return [
            cls(
                id=uuid4(),
                role=RoleType.elem_from_str(msg['role']),
                content=msg["content"],
                cause_by=Action()
            ) for msg in messages
        ]

    @classmethod
    def from_any(cls, msg: Optional[Union[str, Dict, 'Message']]) -> 'Message':
        """
            For Dict:
                {'role': 'user', 'content': 'xxxx...'}
        """
        try:
            if isinstance(msg, str):
                msg = cls(content=msg)
            elif isinstance(msg, Dict):
                role_type = msg['role']
                content = msg['content']
                msg = cls(content=content, sender=RoleType.elem_from_str(role_type))
        except Exception as e:
            raise NotImplementedError('Message type error: {}'.format(e))
        else:
            return msg

    def __str__(self):
        # if self.instruct_content:
        #     return f"[name: {self.sender if self.sender else 'FromUser'} && role_type: {self.role.val} && message_id: {self.id}]: {self.instruct_content.model_dump()}"
        return f"[name:{self.sender if self.sender else 'FromUser'}  role_type:{self.role.val} message_id:{self.id} reply_to:{self.reply_to}]: {self.content}"

    def __repr__(self):
        """while print in list"""
        return self.__str__()


class SystemMessage(Message):

    def __init__(self, content: str):
        super(SystemMessage, self).__init__(content=content, role=RoleType.SYSTEM)
