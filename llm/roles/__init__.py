"""
@Author: obstacles
@Time:  2025-03-04 14:08
@Description:  
"""
import json
import re
import sys
import asyncio
import importlib
import pkgutil
import inspect

from ollama._types import Message as OMessage
from llm.prompts import prompt_setting
from llm.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator, field_validator, SerializeAsAny
from typing import Optional, List, Iterable, Literal, Set, Dict, Tuple, Type, Any, Union
from constant.llm import RoleType
from logs import logger_factory
from constant.llm import TOKEN_COSTS, MessageRouter
from asyncio import Queue, QueueEmpty
from llm.nodes import LLMNode, OpenAINode
from llm.messages import Message
from llm.envs import Env
from llm.memory import Memory
from utils.common import any_to_str
from capture import Capture
from llm.tools import ToolArgs
from llm.nodes import OllamaNode
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from contextlib import AsyncExitStack
from utils.path import root_dir
from constant.client import McpTransportMethod
from typing import Annotated, Dict, TypedDict, Any, Required, NotRequired, ClassVar, cast
from llm.tools import ToolArgs
from pydantic.fields import FieldInfo
from llm.tools import Toolkit


lgr = logger_factory.llm


class ModelFields(TypedDict):
    name: Required[FieldInfo]
    desc: Required[FieldInfo]
    intermediate: Required[FieldInfo]
    args: NotRequired[ToolArgs]


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


class RoleContext(BaseModel):
    env: Env = Field(default=None)
    buffer: Buffer = Field(default_factory=Buffer, exclude=True)
    memory: Memory = Field(default_factory=Memory)
    news: List[Message] = Field(default=None, description='New messages need to be handled')
    subscribe_sender: set[str] = Field(default={}, description='Subscribe role name for solution-subscription mechanism')
    max_react_loop: int = Field(default=5, description='Max react loop number')
    state: int = Field(default=-1, description='State of the action')
    todos: List[Tuple] = Field(default=None, exclude=True, description='tools waited to call and arguments dict')
    action_taken: int = 0


class Role(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(default='obstacles', description='role name')
    goal: str = ''
    skill: str = ''
    constraints: str = Field(
        default='utilize the same language as the user requirements for seamless communication',
        validate_default=True
    )
    address: set[str] = Field(default=set(), description='', validate_default=True)

    toolkit: Toolkit = Field(default_factory=Toolkit, validate_default=True)
    states: List[str] = Field(default=[], validate_default=True, description='Action to state number map')

    identity: RoleType = Field(default=RoleType.USER, description='Role identity')
    agent_node: LLMNode = Field(default_factory=OpenAINode, description='LLM node')
    rc: RoleContext = Field(default_factory=RoleContext)

    cp: SerializeAsAny[Capture] = Field(default_factory=Capture, validate_default=True, description='Capture exception')

    __hash__ = object.__hash__

    @model_validator(mode='after')
    def check_address(self):
        if not self.address:
            self.address = {f'{any_to_str(self)}.{self.name}'}

    @property
    def sys_think_msg(self) -> Optional[Dict[str, str]]:
        return {'role': RoleType.SYSTEM.val, 'content': self.role_definition}

    @property
    def sys_react_msg(self) -> Optional[Dict[str, str]]:
        return {'role': RoleType.SYSTEM.val, 'content': self.role_definition}

    @property
    def role_definition(self) -> str:
        env = self._env_prompt
        name_exp = f'You are {self.name}, an all-capable AI assistant.'
        skill_exp = f'skill at {self.skill},' if self.skill else ''
        goal_exp = f'your goal is {self.goal}.' if self.goal else ''
        tool_exp = ('You have some tools that you can use to help the user,'
                    ' but ultimately you need to give a final reply prefix with END, like "END you final reply here", '
                    'Let others know that your part is done.')
        finish_exp = "If you think you've accomplished your goal, prefix your final reply with 'END you reply'."
        definition = env + name_exp + skill_exp + goal_exp + tool_exp
        return definition

    @property
    def interested_actions_text(self) -> str:
        return ','.join(list(map(lambda x: x.__name__, self.interested_actions)))

    @property
    def intermediate_sender(self):
        """Make sure that sender will not be subscribed by others"""
        return f'{self.name}_intermediate'

    def _reset(self):
        self.states = []
        self.toolkit = []

    def set_tools(self, tools: List[Type[BaseTool]]):
        self.toolkit.add_tools(tools)

    def set_interested_actions(self, actions: Set[Type[BaseTool]]):
        for action in actions:
            self.interested_actions.add(action)

    async def _perceive(self, ignore_history: bool = False) -> bool:
        news = self.rc.buffer.pop_all()
        history = [] if ignore_history else self.rc.memory.get()
        new_list = []
        for n in news:
            if n not in history:
                self.rc.memory.add_one(n)

            if (n.sender in self.rc.subscribe_sender
                    or self.address & n.receiver
                    or MessageRouter.ALL.val in n.receiver):
                if n not in history:
                    new_list.append(n)
        self.rc.news = new_list
        if len(self.rc.news) == 0:
            lgr.debug(f'{self} no new messages, waiting.')
        else:
            new_texts = [f'{m.role.val}: {m.content[:20]}...' for m in self.rc.news]
            lgr.debug(f'{self} perceive {new_texts}.')
        return True if len(self.rc.news) > 0 else False

    async def _think(self) -> Optional[Tuple[bool, str]]:

        message = [self.sys_think_msg] + Message.to_message_list(self.rc.memory.get())
        think = await self.agent_node.achat(message, tools=self.toolkit.param_list)
        if isinstance(think, List):  # call tool
            todos = []
            for call_tool in think:
                todo = self.toolkit.tools.get(call_tool.function.name)
                todo_args = call_tool.function.arguments if call_tool.function.arguments else {}
                todos.append((todo, todo_args))

                # add in memory
                call_message = Message.from_any(
                    msg=f'call tool {todo.name}; args {json.dumps(todo_args, ensure_ascii=False)}',
                    role=RoleType.ASSISTANT
                )
                self.rc.memory.add_one(call_message)

            self.rc.todos = todos
            return True, ''
        elif isinstance(think, str):  # think resp
            if think.startswith('END '):
                return False, think.lstrip('END ')
        else:
            raise RuntimeError(f'Unexpected think type: {type(think)}')


        # else:
        #     self.rc.state = int(choose_state)
        #     self.rc.todo = self.toolkit[self.rc.state]
        #     if self.rc.todo.__annotations__.get('args'):
        #         self.rc.todo.args = self.rc.todo.__annotations__['args'](**think_arguments)
        #     lgr.debug(f"{self} will do {self.rc.todo}.")
        return True

    async def _react(self) -> Optional[Message]:
        messages = [self.sys_react_msg] + self.rc.memory.to_dict()
        for todo in self.rc.todos:
            resp = await todo[0].run(**todo[1])
            message = Message.from_any(resp, role=RoleType.TOOL)
            self.rc.buffer.put_one_msg(message)
            self.rc.action_taken += 1
        if self.rc.env:
            self.rc.env.publish_message(resp)
        return resp

    async def run(self, with_message: Optional[Union[str, Dict, Message]] = None, ignore_history: bool = False) -> Optional[Message]:
        if with_message:
            msg = Message.from_any(with_message)
            self.rc.buffer.put_one_msg(msg)

        self.rc.action_taken = 0
        resp = Message(content='No action taken yet', role=RoleType.SYSTEM)
        while self.rc.action_taken < self.rc.max_react_loop:
            perceive = await self._perceive()
            if not perceive:
                break
            todo, reply = await self._think()
            if not todo:
                return reply
            resp = await self._react()
        self.rc.state = -1
        self.rc.todo = None
        return resp

    @property
    def _env_prompt(self):
        prompt = ''
        if self.rc.env and self.rc.env.desc:
            other_roles = self.rc.env.members.difference({self})
            env_desc = f'You in a environment called {self.rc.env.name} {self.rc.env.desc} with roles {", ".join(map(str, other_roles))}.'
            prompt += env_desc
        return prompt

    def __str__(self):
        return f'{self.name}({self.identity.val})'

    def __repr__(self):
        return self.__str__()


class McpRole(Role):

    conn_type: McpTransportMethod = McpTransportMethod.STDIO
    exit_stack: AsyncExitStack = Field(default_factory=lambda: AsyncExitStack(), validate_default=True)
    session: Optional[ClientSession] = Field(default=None, description='Session used for communication.')
    server_script: str = Field(default=str(root_dir() / 'mcpp' / 'server.py'), description='Server script')
    action_map: Dict[str, Type[BaseTool]] = Field(default={}, description='Action map')

    async def _initialize_session(self):
        server_params = StdioServerParameters(command=sys.executable, args=[self.server_script])
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    # async def _initialize_tool_map(self):
    #     action_map = {}
    #     for _, module_name, _ in pkgutil.iter_modules(tools.__path__):
    #         if module_name == '__init__':
    #             continue
    #         module = importlib.import_module(f'llm.tools.{module_name}')
    #         for name, obj in inspect.getmembers(module, inspect.isclass):
    #             if issubclass(obj, BaseTool) and obj is not BaseTool:
    #                 model_fields: ModelFields = cast(ModelFields, obj.model_fields)
    #                 obj_name = model_fields['name'].default
    #                 action_map[obj_name] = obj
    #     self.action_map = action_map

    async def _initialize_tools(self):
        actions = await self.mcp_tool_to_actions()
        self.set_tools(list(actions.values()))

    def model_post_init(self, __context: Any, *args, **kwargs) -> None:
        asyncio.run(self._initialize_session())
        asyncio.run(self._initialize_action_map())
        asyncio.run(self._initialize_actions())
        lgr.debug(f'[{self.name}] mcp client initial successfully')

    async def mcp_tool_to_actions(self) -> Dict[str, Type[BaseTool]]:
        resp = await self.session.list_tools()
        rsp = {}
        for tool in resp.tools:
            if tool.name in self.action_map:
                rsp[tool.name] = self.action_map[tool.name]
        return rsp

