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

from llm import actions
from llm.prompts import prompt_setting
from llm.actions import Action
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
from llm.actions import ActionArgs,  IntermediateAction
from llm.nodes import OllamaNode
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from contextlib import AsyncExitStack
from utils.path import root_dir
from constant.client import McpTransportMethod
from typing import Annotated, Dict, TypedDict, Any, Required, NotRequired, ClassVar, cast
from llm.actions import ActionArgs
from pydantic.fields import FieldInfo


lgr = logger_factory.llm


class ModelFields(TypedDict):
    name: Required[FieldInfo]
    desc: Required[FieldInfo]
    intermediate: Required[FieldInfo]
    args: NotRequired[ActionArgs]


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
    interested_action: set[str] = Field(default={}, description='Interested action')
    max_react_loop: int = Field(default=5, description='Max react loop number')
    state: int = Field(default=-1, description='State of the action')
    todo: Action = Field(default=None, exclude=True, description='Action to do')
    action_taken: int = 0


class Role(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(default='obstacles', description='role name')
    goal: str = ''
    skill: str = ''
    think_extra_demands: str = ''
    react_extra_demands: str = ''
    constraints: str = Field(
        default='utilize the same language as the user requirements for seamless communication',
        validate_default=True
    )
    address: set[str] = Field(default=set(), description='', validate_default=True)

    actions: List[Action] = Field(default=[], validate_default=True, description='Action list can be performed')
    states: List[str] = Field(default=[], validate_default=True, description='Action to state number map')

    identity: RoleType = Field(default=RoleType.USER, description='Role identity')
    agent_node: LLMNode = Field(default_factory=OpenAINode, description='LLM node')
    rc: RoleContext = Field(default_factory=RoleContext)
    think_answer: Message = Field(
        default=None,
        description='Due to some llm tools called training， May get final answer from think.'
    )

    interested_actions: Set[Type[Action]] = Field(
        default=set(),
        description='user will receiver their interested actions'
    )

    cp: SerializeAsAny[Capture] = Field(default_factory=Capture, validate_default=True, description='Capture exception')

    __hash__ = object.__hash__

    @model_validator(mode='after')
    def check_address(self):
        if not self.address:
            self.address = {f'{any_to_str(self)}.{self.name}'}

    @property
    def sys_think_msg(self) -> Optional[Dict[str, str]]:
        extra_demands = f'Here are some extra demands on you: {self.think_extra_demands}.' if self.think_extra_demands else "You don't have extra demands."
        return {'role': RoleType.SYSTEM.val, 'content': self.role_definition + extra_demands}

    @property
    def sys_react_msg(self) -> Optional[Dict[str, str]]:
        extra_demands = f'Here are some extra demands on you: {self.react_extra_demands}.' if self.react_extra_demands else "You don't have extra demands."
        exp = f'When you get a message from {self.name}_intermediate, you need a summary of the output of your intermediate action to visualize a good output'
        return {'role': RoleType.SYSTEM.val, 'content': self.role_definition + exp + extra_demands}

    @property
    def role_definition(self) -> str:
        env = self._env_prompt
        name_exp = f'You name is {self.name}.' if self.name else ''
        skill_exp = f'You skill at {self.skill}.' if self.skill else ''
        goal_exp = f'You goal is {self.goal}.' if self.goal else ''
        constraints_exp = f'You constraints is {self.constraints}.' if self.constraints else ''
        definition = env + name_exp + skill_exp + goal_exp + constraints_exp
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
        self.actions = []

    def set_actions(self, actions: List[Union[Action, Type[Action]]]):
        for action in actions:
            act_obj = action()
            intermediate_exp = '(intermediate action)' if act_obj.intermediate else ''
            args_prompt = ''
            for field_name, field_info in act_obj.model_fields.items():
                args_model = field_info.annotation
                if field_name == 'args' and issubclass(field_info.annotation, ActionArgs) and args_model is not ActionArgs:
                    args = []
                    for arg_name, arg_info in args_model.model_fields.items():
                        field_type = args_model.__annotations__[arg_name].__name__
                        is_required = arg_info.is_required()
                        description = arg_info.description
                        arg_prompt = f"     {arg_name}({field_type}): {description}"
                        args.append(arg_prompt)
                    args_prompt = '\n'.join(args) + '\n'
            self.actions.append(act_obj)
            states = f'{len(self.actions) - 1}. {act_obj.name}{intermediate_exp}: {act_obj.desc}\n'
            if args_prompt:
                states += args_prompt
            self.states.append(states)

    def set_interested_actions(self, actions: Set[Type[Action]]):
        for action in actions:
            self.interested_actions.add(action)

    async def _perceive(self, ignore_history: bool = False) -> bool:
        news = self.rc.buffer.pop_all()
        history = [] if ignore_history else self.rc.memory.get()
        new_list = []
        for n in news:
            if n in history and isinstance(n.cause_by, IntermediateAction) and n.cause_by.role_name == self.name:
                pass
            else:
                self.rc.memory.add_one(n)

            if isinstance(n.cause_by, IntermediateAction) and n.cause_by.role_name == self.name:
                new_list.append(n)
                continue
            if (n.sender in self.rc.subscribe_sender
                    or self.address & n.receiver
                    or MessageRouter.ALL.val in n.receiver
                    or n.cause_by in self.interested_actions):
                if n not in history:
                    new_list.append(n)
        self.rc.news = new_list
        if len(self.rc.news) == 0:
            lgr.debug(f'{self} no new messages, waiting.')
        else:
            new_texts = [f'{m.role.val}: {m.content[:20]}...' for m in self.rc.news]
            lgr.debug(f'{self} perceive {new_texts}.')
        return True if len(self.rc.news) > 0 else False

    async def _think(self) -> Optional[Union[bool, List[Dict]]]:
        state_template = prompt_setting.COMMON_STATE_TEMPLATE
        prompt = (
            state_template
            .replace('{history}', '\n'.join(map(str, self.rc.memory.get())))
            .replace('{states}', ''.join(self.states))
            .replace('{n_states}', str(len(self.states) - 1))
            .replace('{previous_state}', str(self.rc.state))
            .replace('{intermediate_name}', f'{self.name}_intermediate')
        )

        message = {'role': RoleType.USER.val, 'content': prompt}
        think = await self.agent_node.achat([self.sys_think_msg, message])
        if isinstance(self.agent_node, OllamaNode):
            pattern = r'\{"state":\s*\d+,\s*"arguments":\s*\{.*?\}\}'
            match = re.search(pattern, think, re.DOTALL)
            if match:
                think = match.group().lstrip('```json').rstrip('```')
            elif re.search(r'\{"state":\s*\d+}', think, re.DOTALL):
                think = re.search(r'\{"state":\s*\d+}', think, re.DOTALL).group().lstrip('```json').rstrip('```')
            else:
                raise RuntimeError(f'unable to parse {think}')
        think = json.loads(think)
        choose_state = think.get('state')
        think_arguments = think.get('arguments')
        # llama 3.1 8B will put final answer in this field
        condition = think_arguments.get('message')
        if condition:
            lgr.debug(f'{self.name} get final answer through think: {think_arguments["message"]}')
            self.think_answer = Message.from_any(think_arguments.get('message'), sender=self.name, reply_to=self.rc.memory.get()[-1].id, role=RoleType.ASSISTANT)
            return True
        if int(choose_state) == -1:
            lgr.debug(f"{self} is idle.")
            return False
        else:
            self.rc.state = int(choose_state)
            self.rc.todo = self.actions[self.rc.state]
            if self.rc.todo.__annotations__.get('args'):
                self.rc.todo.args = self.rc.todo.__annotations__['args'](**think_arguments)
            lgr.debug(f"{self} will do {self.rc.todo}.")
            return True

    async def _react(self) -> Optional[Message]:
        if not self.think_answer:
            messages = [self.sys_react_msg] + self.rc.memory.to_dict(ample=True)
            resp = await self.rc.todo.run(messages, llm=self.agent_node)
            if self.rc.todo.intermediate:
                resp_msg = Message(
                    content=resp,
                    role=self.identity,
                    cause_by=IntermediateAction(role_name=self.name),
                    sender=self.intermediate_sender,
                    reply_to=self.rc.memory.get()[-1].id,
                    receiver={self.name}
                )
            else:
                resp_msg = Message(
                    content=resp,
                    role=self.identity,
                    cause_by=self.rc.todo,
                    sender=self.name,
                    reply_to=self.rc.memory.get()[-1].id,
                )
        else:
            resp_msg = self.think_answer
        self.rc.memory.add_one(resp_msg)
        self.rc.action_taken += 1
        if self.rc.env:
            self.rc.env.publish_message(resp_msg)
        if self.rc.todo.intermediate:
            self.rc.buffer.put_one_msg(resp_msg)
        return resp_msg

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
            todo = await self._think()
            if not todo:
                break
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
    action_map: Dict[str, Type[Action]] = Field(default={}, description='Action map')

    async def _initialize_session(self):
        server_params = StdioServerParameters(command=sys.executable, args=[self.server_script])
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def _initialize_action_map(self):
        action_map = {}
        for _, module_name, _ in pkgutil.iter_modules(actions.__path__):
            if module_name == '__init__':
                continue
            module = importlib.import_module(f'llm.actions.{module_name}')
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Action) and obj is not Action:
                    model_fields: ModelFields = cast(ModelFields, obj.model_fields)
                    obj_name = model_fields['name'].default
                    action_map[obj_name] = obj
        self.action_map = action_map

    async def _initialize_actions(self):
        actions = await self.mcp_tool_to_actions()
        self.set_actions(list(actions.values()))

    def model_post_init(self, __context: Any, *args, **kwargs) -> None:
        asyncio.run(self._initialize_session())
        asyncio.run(self._initialize_action_map())
        asyncio.run(self._initialize_actions())
        lgr.debug(f'[{self.name}] mcp client initial successfully')

    async def mcp_tool_to_actions(self) -> Dict[str, Type[Action]]:
        resp = await self.session.list_tools()
        rsp = {}
        for tool in resp.tools:
            if tool.name in self.action_map:
                rsp[tool.name] = self.action_map[tool.name]
        return rsp

