"""
@Author: obstacles
@Time:  2025-03-10 17:15
@Description:  
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Iterable, Literal
from puti.constant.llm import RoleType
from typing import Dict, Tuple, Type, Any, Union
from datetime import datetime
from uuid import uuid4
from puti.constant.llm import MessageTag, MessageTag
from puti.utils.common import any_to_str, import_class
from puti.llm.tools import BaseTool


class Message(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    sender: str = Field(default='', validate_default=True, description='Sender role name')
    receiver: set['str'] = Field(default={MessageTag.ALL.val}, validate_default=True, description='Receiver role name')
    reply_to: str = Field(default='', description='Message id reply to')
    id: str = Field(default_factory=lambda: str(uuid4())[:8], description='Unique code of messages')
    content: str = ''
    instruct_content: Optional[BaseModel] = Field(default=None, validate_default=True)
    role: RoleType = Field(default=RoleType.USER, validate_default=True)
    attachment_urls: List[str] = Field(default=[], validate_default=True, description='URLs of attachments for multi modal')
    created_time: datetime = Field(default=datetime.now(), validate_default=True)
    tool_call_id: str = Field(default='', description='Tool call id')

    non_standard: Any = Field(default=None, description='Non-standard dic', exclude=True)

    think_process: str = Field(default='', description='Thinking process for message')

    def update_content(self, new_content: str):
        """Updates the content of the message."""
        self.content = new_content

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

    @classmethod
    def to_ollama3_format(cls, messages: List['Message']) -> str:
        """
            ollama3 format
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>

            {{ system_prompt }}<|eot_id|><|start_header_id|>user<|end_header_id|>

            {{ user_message_1 }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

            {{ model_answer_1 }}<|eot_id|><|start_header_id|>user<|end_header_id|>

            {{ user_message_2 }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
        """
        messages = cls.to_message_list(messages)
        # 开始标记
        prompt = "<|begin_of_text|>"

        # 如果有 system 消息，就先处理 system
        # 并且只取第一个 system 消息，当做系统提示
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"].strip()
                prompt += (
                    "<|start_header_id|>system<|end_header_id|>\n\n"
                    f"{system_text}<|eot_id|>"
                )
                break

        # 遍历所有非 system 消息，按顺序拼接 user/assistant
        for msg in messages:
            role = msg["role"]
            if role == "system":
                continue
            text = msg["content"].strip()
            prompt += (
                f"<|start_header_id|>{role}<|end_header_id|>\n\n"
                f"{text}<|eot_id|>"
            )

        # 最后留给 assistant 继续回复
        prompt += "<|start_header_id|>assistant<|end_header_id|>"
        return prompt

    def to_message_dict(self, ample: bool = True) -> dict:
        if self.non_standard:
            return self.non_standard
        resp = {'role': self.role.val, 'content': self.ample_content if ample else self.content}
        if self.tool_call_id:
            resp['tool_call_id'] = self.tool_call_id
        return resp

    @property
    def ample_content(self):
        """ If other agent wish to see detail info """
        if self.non_standard:
            return self.non_standard
        reply_to_exp = f' reply_to:{self.reply_to}' if self.reply_to else ''
        return f"{self.sender}({self.role.val}): {self.content}"

    def is_user_message(self):
        return self.role == RoleType.USER

    def is_assistant_message(self):
        return self.role == RoleType.ASSISTANT

    def is_tool_message(self):
        return self.role == RoleType.TOOL

    def __str__(self):
        if self.non_standard:
            return f'{self.non_standard}'
        reply_to_exp = f' reply_to:{self.reply_to}' if self.reply_to else ''
        return f"{self.sender if self.sender else 'FromUser'}({self.role.val}) {reply_to_exp}: {self.content}"

    def __repr__(self):
        """while print in list"""
        return self.__str__()


class SystemMessage(Message):

    def __init__(self, content: str, **kwargs):
        super(SystemMessage, self).__init__(content=content, role=RoleType.SYSTEM, **kwargs)


class AssistantMessage(Message):

    def __init__(self, content: str, **kwargs):
        super(AssistantMessage, self).__init__(content=content, role=RoleType.ASSISTANT, **kwargs)


class UserMessage(Message):

    def __init__(self, content: str, **kwargs):
        super(UserMessage, self).__init__(content=content, role=RoleType.USER, **kwargs)


class ToolMessage(Message):

    def __init__(self, *, non_standard, **kwargs):
        """We can use non_standard to store the tool message"""
        super(ToolMessage, self).__init__(non_standard=non_standard, role=RoleType.TOOL, **kwargs)

