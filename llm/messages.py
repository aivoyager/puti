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
from llm.tools import BaseTool


class Message(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # if design in role will loop import
    cause_by: Optional[BaseTool] = Field(default=None, description='message initiator Action str', validate_default=True)
    sender: str = Field(default='', validate_default=True, description='Sender role name')
    receiver: set['str'] = Field(default={MessageRouter.ALL.val}, validate_default=True, description='Receiver role name')
    reply_to: str = Field(default='', description='Message id reply to')
    id: str = Field(default_factory=lambda: str(uuid4())[:8], description='Unique code of messages')
    content: str = ''
    instruct_content: Optional[BaseModel] = Field(default=None, validate_default=True)
    role: RoleType = Field(default=RoleType.USER, validate_default=True)
    attachment_urls: List[str] = Field(default=[], validate_default=True, description='URLs of attachments for multi modal')
    created_time: datetime = Field(default=datetime.now(), validate_default=True)

    @field_validator('cause_by', mode='before')
    @classmethod
    def check_cause_by(cls, cause_by: Any):
        return cause_by

    @classmethod
    def from_messages(cls, messages: List[dict]) -> List["Message"]:

        return [
            cls(
                id=uuid4(),
                role=RoleType.elem_from_str(msg['role']),
                content=msg["content"],
                cause_by=BaseTool()
            ) for msg in messages
        ]

    @classmethod
    def from_any(cls, msg: Optional[Union[str, Dict, 'Message']], **kwargs) -> 'Message':
        """
            For Dict:
                {'role': 'user', 'content': 'xxxx...'}
        """
        try:
            if isinstance(msg, str):
                msg = cls(content=msg, **kwargs)
            elif isinstance(msg, Dict):
                role_type = msg['role']
                content = msg['content']
                msg = cls(content=content, sender=RoleType.elem_from_str(role_type), **kwargs)
        except Exception as e:
            raise NotImplementedError('Message type error: {}'.format(e))
        else:
            return msg

    @classmethod
    def to_message_list(cls, messages: List['Message']) -> List[dict]:
        return [msg.to_message_dict() for msg in messages]

    def to_message_dict(self, ample: bool = False) -> dict:
        return {'role': self.role.val, 'content': self.ample_content if ample else self.content}

    @property
    def ample_content(self):
        reply_to_exp = f' reply_to:{self.reply_to}' if self.reply_to else ''
        return f"[name:{self.sender if self.sender else 'FromUser'}  role_type:{self.role.val} message_id:{self.id}{reply_to_exp}]: {self.content}"

    def __str__(self):
        reply_to_exp = f' reply_to:{self.reply_to}' if self.reply_to else ''
        return f"[name:{self.sender if self.sender else 'FromUser'}  role_type:{self.role.val} message_id:{self.id}{reply_to_exp}]: {self.content}"

    def __repr__(self):
        """while print in list"""
        return self.__str__()


class SystemMessage(Message):

    def __init__(self, content: str):
        super(SystemMessage, self).__init__(content=content, role=RoleType.SYSTEM)
