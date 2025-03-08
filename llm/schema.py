"""
@Author: obstacles
@Time:  2025-03-04 14:10
@Description:  
"""
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field, ConfigDict, create_model, model_validator, PrivateAttr, SerializeAsAny
from typing import Optional, List, Iterable
from constant.llm import RoleType
from logs import logger_factory
from typing import Dict, Tuple, Type, Any, Union
from conf.llm_config import LLMConfig, OpenaiConfig
from openai import AsyncOpenAI
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import uuid4
from constant.llm import TOKEN_COSTS, MessageRouter
from asyncio import Queue, QueueEmpty

lgr = logger_factory.default


class Env(BaseModel):
    id: str = Field(default_factory=lambda: uuid4(), validate_default=True, description='Unique code of messages')
    messages: List[Dict] = None
    children_envs: List['Env'] = None
    parent_env: 'Env' = None
    members: Dict[str, set[str]] = Field(default=None, description='key is role name, value is role address')


class Cost(BaseModel):
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_budget: float = 0
    max_budget: float = 10.0
    total_cost: float = 0
    token_costs: dict[str, dict[str, float]] = TOKEN_COSTS

    def update_cost(self, prompt_tokens, completion_tokens, model):
        """ Update cose """


class LLMNode(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    llm_name: str = Field(default='openai', description='Random llm name.')
    conf: LLMConfig = Field(default_factory=OpenaiConfig, validate_default=True)
    system_prompt: List[dict] = [{'role': RoleType.SYSTEM.val, 'content': 'You are a helpful assistant.'}]
    acli: Optional[Union[AsyncOpenAI]] = Field(None, description='Cli connect with llm.')
    cost: Optional[Cost] = None

    def model_post_init(self, __context):
        if not self.acli:
            self.acli = AsyncOpenAI(base_url=self.conf.BASE_URL, api_key=self.conf.API_KEY)

    def create_model_class(cls, class_name: str, mapping: Dict[str, Tuple[Type, Any]]):
        """基于pydantic v2的模型动态生成，用来检验结果类型正确性"""

        def check_fields(cls, values):
            all_fields = set(mapping.keys())
            required_fields = set()
            for k, v in mapping.items():
                type_v, field_info = v
                if LLMNode.is_optional_type(type_v):
                    continue
                required_fields.add(k)

            missing_fields = required_fields - set(values.keys())
            if missing_fields:
                raise ValueError(f"Missing fields: {missing_fields}")

            unrecognized_fields = set(values.keys()) - all_fields
            if unrecognized_fields:
                lgr.warning(f"Unrecognized fields: {unrecognized_fields}")
            return values

        validators = {"check_missing_fields_validator": model_validator(mode="before")(check_fields)}

        new_fields = {}
        for field_name, field_value in mapping.items():
            if isinstance(field_value, dict):
                # 对于嵌套结构，递归创建模型类
                nested_class_name = f"{class_name}_{field_name}"
                nested_class = cls.create_model_class(nested_class_name, field_value)
                new_fields[field_name] = (nested_class, ...)
            else:
                new_fields[field_name] = field_value

        new_class = create_model(class_name, __validators__=validators, **new_fields)
        return new_class

    @abstractmethod
    def achat(self, messages: List[Dict]) -> str:
        """ Async chat """


class Action(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(..., description='Action name')
    node: LLMNode = None


class UserRequirements(Action):
    """From user demands"""
    name: str = 'user requirements'


class Message(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # if design in role will loop import
    sender: str = Field(default='', validate_default=True, description='Sender role name')
    receiver: set['str'] = Field(default={MessageRouter.ALL.val}, validate_default=True, description='Receiver role name')
    id: str = Field(default_factory=lambda: uuid4(), description='Unique code of messages')
    content: str = ''
    instruct_content: Optional[BaseModel] = Field(default=None, validate_default=True)
    role: RoleType = Field(default=RoleType.USER, validate_default=True)
    cause_by: Action = Field(default_factory=lambda: UserRequirements(), validate_default=True, description='Reason for cause this message')
    attachment_urls: List[str] = Field(default=[], validate_default=True, description='URLs of attachments for multi modal')
    created_time: datetime = Field(default=datetime.now(), validate_default=True)

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


class Buffer(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _queue: Queue = PrivateAttr(default_factory=Queue)

    def put_one_msg(self, msg: Message):
        self._queue.put_nowait(msg)

    def pop_one(self) -> Optional[Message]:
        try:
            item = self._queue.get_nowait()
            if item:
                # indicate that task already done
                self._queue.task_done()
            return item
        except QueueEmpty:
            return None

    def pop_all(self) -> List[Message]:
        resp = []
        while True:
            msg = self.pop_one()
            if not msg:
                break
            resp.append(msg)
        return resp


class Memory(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    storage: List[SerializeAsAny['Message']] = []

    def get(self, k=0) -> List[Message]:
        """ top k , 0 for all"""
        return self.storage[-k:]

    def add_one(self, message: Message):
        self.storage.append(message)

    def add_batch(self, messages: Iterable[Message]):
        for msg in messages:
            self.add_one(msg)


class RoleContext(BaseModel):
    env: Env = Field(default=None)
    buffer: Buffer = Field(default_factory=Buffer, exclude=True)
    memory: Memory = Field(default_factory=Memory)
    news: List[Message] = Field(default=None, description='New messages need to be handled')
    subscribe_sender: set[str] = Field(default={}, description='Subscribe role name for solution-subscription mechanism')


class Role(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(..., description='Role name')
    address: set[str] = set()
    system_message: 'SystemMessage' = Field(default=None, description='System message')
    actions: List[Action] = []
    state: int
    identity: RoleType = Field(default=RoleType.USER, description='Role identity')
    agent_node: LLMNode = None
    rc: RoleContext = Field(default_factory=RoleContext)

    async def run(self, with_message: Optional[str, Dict, Message] = None, ignore_history: bool = False) -> Optional[Message]:
        if with_message:
            msg = None
            if isinstance(with_message, str):
                msg = Message(content=with_message)
            elif isinstance(with_message, Message):
                msg = with_message
            elif isinstance(with_message, Dict):
                u_name = next(iter(with_message.keys()))
                if u_name not in RoleType.keys():
                    raise KeyError('Unknown role: {}'.format(u_name))
                with_message = next(iter(with_message.values()))
                msg = Message(content=with_message, sender=u_name)
            else:
                raise TypeError('with_message must be str or dict or `Message`')
        self.rc.buffer.put_one_msg(msg)

        news = self.rc.buffer.pop_all()
        self.rc.memory.add_batch(news)

        history = [] if ignore_history else self.rc.memory.get()
        self.rc.news =

        watch_resp = self._wathch()

    async def _watch(self):
        news = []
        if not news:
            news = self.rc.buffer.pop_all()
        old_msgs = self.rc.memory.get()


class SystemMessage(Message):

    def __init__(self, content: str):
        super(SystemMessage, self).__init__(content=content, role=RoleType.SYSTEM)


