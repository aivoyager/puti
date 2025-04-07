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
import threading

from functools import partial
from ollama._types import Message as OMessage
from llm.prompts import prompt_setting
from llm import tools
from llm.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator, field_validator, SerializeAsAny
from typing import Optional, List, Iterable, Literal, Set, Dict, Tuple, Type, Any, Union
from constant.llm import RoleType
from logs import logger_factory
from constant.llm import TOKEN_COSTS, MessageRouter
from asyncio import Queue, QueueEmpty
from llm.nodes import LLMNode, OpenAINode
from llm.messages import Message, ToolMessage, AssistantMessage, UserMessage
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
from openai.types.chat.chat_completion_message import ChatCompletionMessage


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
    address: set[str] = Field(default=set(), description='', validate_default=True)
    toolkit: Toolkit = Field(default_factory=Toolkit, validate_default=True)
    identity: RoleType = Field(default=RoleType.ASSISTANT, description='Role identity')
    agent_node: LLMNode = Field(default_factory=OpenAINode, description='LLM node')
    rc: RoleContext = Field(default_factory=RoleContext)
    answer: Optional[Message] = Field(default=None, description='assistant answer')

    tool_calls_one_round: List[str] = Field(default=[], description='tool calls one round contains tool call id')

    cp: SerializeAsAny[Capture] = Field(default_factory=Capture, validate_default=True, description='Capture exception')

    __hash__ = object.__hash__

    @model_validator(mode='after')
    def check_address(self):
        if not self.address:
            self.address = {f'{any_to_str(self)}.{self.name}'}

    @property
    def sys_think_msg(self) -> Optional[Dict[str, str]]:
        return {'role': RoleType.SYSTEM.val, 'content': self._env_prompt + self.role_definition}

    @property
    def sys_react_msg(self) -> Optional[Dict[str, str]]:
        return {'role': RoleType.SYSTEM.val, 'content': self.role_definition}

    @property
    def role_definition(self) -> str:
        name_exp = f'You name is {self.name}, an helpful AI assistant,'
        skill_exp = f'skill at {self.skill},' if self.skill else ''
        goal_exp = f'your goal is {self.goal}.' if self.goal else ''
        constraints_exp = (
            'You constraint is utilize the same language for seamless communication'
            ' and always give a clearly in final reply with format json format {"FINAL_ANSWER": Your final answer here}'
            ' do not give ANY other information except this json.'
            ' Pay attention to historical information to distinguish and make decision.'
       )
        tool_exp = (
            'You have some tools that you can use to help the user or meet user needs, '
            'fully understand the tool functions and their arguments before using them,'
            'make sure the types and values of the arguments you provided to the tool functions are correct'
            'and always provide parameters that must be worn, '
            'tools give you only the intermediate product, '
            'no matter whether use tool or not,'
            'ultimately you need to give a clearly final reply prefix with END like "END you final reply here",'
            'let others know that your part is done.'
            'If there is an error in calling the tool, you need to fix it yourself.'
        )
        finish_exp = ("Based on user requirements and your prior knowledge to jude "
                      "if you've accomplished your goal, prefix your final reply with 'END you reply'.")
        # definition = name_exp + skill_exp + goal_exp + constraints_exp + tool_exp
        definition = name_exp + skill_exp + goal_exp + constraints_exp
        return definition

    def publish_message(self):
        if not self.answer:
            return
        if self.answer and self.rc.env:
            self.rc.env.publish_message(self.answer)
            self.rc.memory.add_one(self.answer)  # this one won't be perceived
            self.answer = None

    def _reset(self):
        self.toolkit = Toolkit()

    def set_tools(self, tools: List[Type[BaseTool]]):
        self.toolkit.add_tools(tools)

    def _correction(self, fix_msg: str):
        lgr.debug("Self-Correction: %s", fix_msg)
        err = UserMessage(content=fix_msg, sender=RoleType.USER.val)
        self.rc.buffer.put_one_msg(err)
        return False, ''

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
        last_msg = message[-1]
        message_pure = []

        if isinstance(last_msg, dict):
            my_prefix = f'{self.name}({self.identity.val}):'
            my_tool_prefix = f'{self.name}({RoleType.TOOL.val}):'
            if not last_msg['content'].startswith(my_prefix) and not last_msg['content'].startswith(my_tool_prefix):
                for msg in message:
                    if not isinstance(msg, dict):
                        if not isinstance(msg, ChatCompletionMessage):
                            message_pure.append(msg)
                            continue
                    else:
                        if not msg['content'].startswith(my_tool_prefix):
                            message_pure.append(msg)
                            continue
        message_pure = message if not message_pure else message_pure

        think: Union[ChatCompletionMessage, str] = await self.agent_node.chat(message_pure, tools=self.toolkit.param_list)

        # llm call tools
        if isinstance(think, ChatCompletionMessage) and think.tool_calls:  # call tool
            think.tool_calls = think.tool_calls[:1]
            todos = []
            for call_tool in think.tool_calls:
                todo = self.toolkit.tools.get(call_tool.function.name)
                todo_args = call_tool.function.arguments if call_tool.function.arguments else {}
                todo_args = json.loads(todo_args) if isinstance(todo_args, str) else todo_args
                tool_call_id = call_tool.id
                self.tool_calls_one_round.append(tool_call_id)
                todos.append((todo, todo_args, tool_call_id))

            # TODO: multiple tools call for openai support
            call_message = Message(non_standard=think)
            self.rc.memory.add_one(call_message)

            self.rc.todos = todos
            return True, ''

        # from openai、ollama, different data structure.
        # llm reply directly
        elif (isinstance(think, ChatCompletionMessage) and think.content) or isinstance(think, str):  # think resp
            try:
                if isinstance(think, str):
                    content = json.loads(think)
                else:
                    content = json.loads(think.content)
                content = content.get('FINAL_ANSWER')
            except json.JSONDecodeError:
                # send to self, no publish, no action
                fix_msg = (f'Your returned an unexpected invalid json data, fix it please, '
                           f'make sure the repaired results include the full process and results rather than summary'
                           f'  ---> {think}')
                return self._correction(fix_msg)

            if content:
                self.answer = AssistantMessage(content=content, sender=self.name)
                return False, content
            else:
                fix_msg = 'Your returned json data does not have a "FINAL ANSWER" key. Please check'
                return self._correction(fix_msg)

        # unexpected think format
        else:
            err = f'Unexpected chat response: {type(think)}'
            lgr.error(err)
            raise RuntimeError(err)

    async def _react(self) -> Optional[Message]:
        message = Message.from_any('no tools taken yet')
        for todo in self.rc.todos:
            run = partial(todo[0].run, llm=self.agent_node)
            try:
                resp = await run(**todo[1])
                resp = json.dumps(resp, ensure_ascii=False) if not isinstance(resp, str) else resp
            except Exception as e:
                message = Message(non_standard_dic={
                    'type': 'function_call_output',
                    'call_id': todo[2],
                    'output': str(e)
                })
                message = Message(content=str(e), sender=self.name, role=RoleType.TOOL, tool_call_id=todo[2])
            else:
                message = Message.from_any(resp, role=RoleType.TOOL, sender=self.name, tool_call_id=todo[2])
            finally:
                self.rc.buffer.put_one_msg(message)
                self.rc.action_taken += 1
                self.answer = message
        return message

    async def run(self, with_message: Optional[Union[str, Dict, Message]] = None, ignore_history: bool = False) -> Optional[Message]:
        if with_message:
            msg = Message.from_any(with_message)
            self.rc.buffer.put_one_msg(msg)

        self.rc.action_taken = 0
        resp = Message(content='No action taken yet', role=RoleType.SYSTEM)
        while self.rc.action_taken < self.rc.max_react_loop:
            perceive = await self._perceive()
            if not perceive:
                self.publish_message()
                break
            todo, reply = await self._think()
            if not todo:
                self.publish_message()
                return reply
            resp = await self._react()
        self.rc.todos = []
        return resp

    @property
    def _env_prompt(self):
        prompt = ''
        if self.rc.env and self.rc.env.desc:
            other_roles = self.rc.env.members.difference({self})
            roles_exp = f' with roles {", ".join(map(str, other_roles))}' if other_roles else ''
            env_desc = f'You in a environment called {self.rc.env.name}({self.rc.env.desc}){roles_exp}. '
            prompt += env_desc
        return prompt

    def __str__(self):
        return f'{self.name}({self.identity.val})'

    def __repr__(self):
        return self.__str__()


class McpRole(Role):

    conn_type: McpTransportMethod = McpTransportMethod.STDIO
    exit_stack: AsyncExitStack = Field(default_factory=AsyncExitStack, validate_default=True)
    session: Optional[ClientSession] = Field(default=None, description='Session used for communication.', validate_default=True)
    server_script: str = Field(default=str(root_dir() / 'mcpp' / 'server.py'), description='Server script')

    initialized: bool = False
    init_lock: asyncio.Lock = Field(default_factory=asyncio.Lock, exclude=True)

    async def _initialize_session(self):
        if self.session:
            await self.disconnect()
        server_params = StdioServerParameters(command=sys.executable, args=[self.server_script])
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def _initialize_tools(self):
        """ initialize a toolkit with all tools to filter mcp server tools """
        # initialize all tools
        for _, module_name, _ in pkgutil.iter_modules(tools.__path__):
            if module_name == '__init__':
                continue
            module = importlib.import_module(f'llm.tools.{module_name}')
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseTool) and obj is not BaseTool:
                    self.toolkit.add_tool(obj)

        # filter tools that server have
        resp = await self.session.list_tools()
        mcp_server_tools = {tool.name for tool in resp.tools}

        self.toolkit.intersection_with(mcp_server_tools, inplace=True)

    async def disconnect(self):
        if self.session and self.exit_stack:
            await self.exit_stack.aclose()
            self.session = None
            self.toolkit = Toolkit()

    async def run(self, *args, **kwargs):
        try:
            await self._initialize()
            resp = await super().run(*args, **kwargs)
            return resp
        finally:
            await self.disconnect()

    async def _initialize(self):
        if self.initialized:
            return
        async with self.init_lock:
            if self.initialized:
                return
            await self._initialize_session()
            await self._initialize_tools()
            self.initialized = True
            lgr.debug(f'[{self.name}] mcp client initial successfully')
