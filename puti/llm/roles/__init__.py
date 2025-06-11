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

from puti.core.resp import ToolResponse
from functools import partial
from ollama._types import Message as OMessage
from puti.llm.prompts import prompt_setting
from puti.llm import tools
from puti.llm.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator, field_validator, SerializeAsAny
from typing import Optional, List, Iterable, Literal, Set, Dict, Tuple, Type, Any, Union
from puti.constant.llm import RoleType
from logs import logger_factory
from puti.constant.llm import TOKEN_COSTS, MessageTag
from asyncio import Queue, QueueEmpty
from puti.llm.nodes import LLMNode, OpenAINode
from puti.llm.messages import Message, ToolMessage, AssistantMessage, UserMessage, SystemMessage
from puti.llm.envs import Env
from puti.llm.memory import Memory
from puti.utils.common import any_to_str, is_valid_json
from capture import Capture
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from contextlib import AsyncExitStack
from puti.utils.path import root_dir
from puti.constant.client import McpTransportMethod
from typing import Annotated, Dict, TypedDict, Any, Required, NotRequired, ClassVar, cast
from pydantic.fields import FieldInfo
from puti.llm.tools import Toolkit, ToolArgs
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from puti.constant.llm import MessageTag, MessageType



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
    max_react_loop: int = Field(default=10, description='Max react loop number')
    state: int = Field(default=-1, description='State of the action')
    todos: List[Tuple] = Field(default=None, exclude=True, description='tools waited to call and arguments dict')
    action_taken: int = 0
    root: str = str(root_dir())


class Role(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(default='obstacles', description='role name')
    goal: str = ''
    skill: str = ''
    identity: str = ''  # e.g. doctor

    address: set[str] = Field(default=set(), description='', validate_default=True)
    toolkit: Toolkit = Field(default_factory=Toolkit, validate_default=True)
    role_type: RoleType = Field(default=RoleType.ASSISTANT, description='Role identity')
    agent_node: LLMNode = Field(default_factory=OpenAINode, description='LLM node')
    rc: RoleContext = Field(default_factory=RoleContext)
    answer: Optional[Message] = Field(default=None, description='assistant answer')

    tool_calls_one_round: List[str] = Field(default=[], description='tool calls one round contains tool call id')
    cp: SerializeAsAny[Capture] = Field(default_factory=Capture, validate_default=True, description='Capture exception')
    think_mode: bool = Field(default=False, description='return think proces')

    __hash__ = object.__hash__  # make sure hashable can be regarded as dict key

    def model_post_init(self, __context: Any) -> None:
        self._init_memory()

    def _init_memory(self):
        # Pass the LLM node to the memory for embedding purposes
        self.rc.memory.llm = self.agent_node
        self.rc.memory.top_k = self.agent_node.conf.FAISS_SEARCH_TOP_K

    @model_validator(mode='after')
    def check_address(self):
        if not self.address:
            self.address = {f'{any_to_str(self)}.{self.name}'}
        return self  # return self for avoiding warning

    @property
    def sys_think_msg(self) -> Optional[Dict[str, str]]:
        if not self.rc.env:
            sys_single_agent = prompt_setting.sys_single_agent.render(
                WORKING_DIRECTORY_PATH=self.rc.root,
                FINAL_ANSWER_KEYWORDS=MessageType.FINAL_ANSWER.val
            )
            think_msg = SystemMessage.from_any(self.role_definition + sys_single_agent).to_message_dict()
        else:
            sys_multi_agent = prompt_setting.sys_multi_agent.render(
                ENVIRONMENT_NAME=self.rc.env.name,
                ENVIRONMENT_DESCRIPTION=self.rc.env.desc,
                AGENT_NAME=self.name,
                OTHERS=', '.join([r.name for r in self.rc.env.members if r.name != self.name]),
                GOAL_SECTION=self.goal,
                SKILL_SECTION=self.skill,
                IDENTITY_SECTION=self.identity,
                SELF=str(self)
            )
            think_msg = SystemMessage.from_any(sys_multi_agent).to_message_dict()
        return think_msg

    @property
    def role_definition(self) -> str:
        name_exp = f'You name is {self.name}'
        skill_exp = f'skill at {self.skill}' if self.skill else ''
        goal_exp = f'your goal is {self.goal}' if self.goal else ''
        definition = ','.join([i for i in [name_exp, skill_exp, goal_exp] if i]) + '.'
        return definition

    async def publish_message(self):
        if not self.answer:
            return

        # For multi angent
        if self.rc.env:
            self.rc.env.publish_message(self.answer)
            await self.rc.memory.add_one(self.answer)  # this one won't be perceived
            self.answer = None
        # For single angent
        else:
            await self.rc.memory.add_one(self.answer)
            self.answer = None

    def _reset(self):
        self.toolkit = Toolkit()

    def set_tools(self, tools: List[Type[BaseTool]]):
        self.toolkit.add_tools(tools)

    def _correction(self, fix_msg: str):
        """ self-correction mechanism """
        # lgr.debug(f"self correction: {fix_msg}")
        err = UserMessage(content=fix_msg, sender=RoleType.USER.val)
        self.rc.buffer.put_one_msg(err)
        self.rc.action_taken += 1
        return False, 'self-correction'

    async def _perceive(self, ignore_history: bool = False) -> bool:
        news = self.rc.buffer.pop_all()
        history = [] if ignore_history else self.rc.memory.get()
        new_list = []
        for n in news:
            if (
                n.sender in self.rc.subscribe_sender
                or self.address & n.receiver
                or MessageTag.ALL.val in n.receiver
            ):
                if n not in history:
                    new_list.append(n)
                    await self.rc.memory.add_one(n)
        self.rc.news = new_list
        # if len(self.rc.news) == 0:
        #     lgr.debug(f'{self} no new messages, waiting.')
        # else:
        #     new_texts = [f'{m.role.val}: {m.content[:80]}...' for m in self.rc.news]
        #     # lgr.debug(f'{self} perceive {new_texts}.')
        return True if len(self.rc.news) > 0 else False

    async def _think(self) -> Optional[Tuple[bool, str]]:
        """
            return:
                bool -> If have a tool call
                str -> `answer` or `self reflection`
        """
        base_system_prompt = self.sys_think_msg

        # Get all messages from memory for this session.
        all_messages = self.rc.memory.get()

        # --- New History Selection Logic ---

        # 1. Get the last user message for the RAG query.
        last_user_message = None
        for msg in reversed(all_messages):
            if msg.role == RoleType.USER:
                last_user_message = msg
                break

        # 2. Perform RAG search on the entire long-term memory.
        relevant_history = []
        if last_user_message and last_user_message.content:
            relevant_history = await self.rc.memory.search(last_user_message.content)

        # 3. Identify the last 5 conversation rounds.
        user_message_indices = [i for i, msg in enumerate(all_messages) if msg.role == RoleType.USER]
        split_index = 0
        if len(user_message_indices) > 5:
            split_index = user_message_indices[-5]
        recent_messages = all_messages[split_index:]

        # 4. Filter retrieved history to exclude items from the recent conversation.
        recent_contents = set()
        for msg in recent_messages:
            if msg.role == RoleType.USER:
                recent_contents.add(f"User asked: {msg.content}")
            elif msg.role == RoleType.ASSISTANT:
                recent_contents.add(f"You responded: {msg.content}")

        filtered_relevant_history = [text for text in relevant_history if text not in recent_contents]

        # 5. Inject filtered relevant history into the system prompt.
        if filtered_relevant_history:
            context_str = "\n".join(filtered_relevant_history)
            enhanced_prompt = prompt_setting.enhanced_memory.render(context_str=context_str)
            enhanced_prompt = base_system_prompt['content'] + enhanced_prompt
            base_system_prompt['content'] = enhanced_prompt

        # 6. Add think tips to the last user message in the recent conversation.
        # if last_user_message and last_user_message in recent_messages:
        #     if prompt_setting.think_tips not in last_user_message.content:
        #         last_user_message.update_content(last_user_message.content + prompt_setting.think_tips)

        # 7. Construct the final message list for the LLM.
        history_messages = recent_messages
        message = [base_system_prompt] + [msg.to_message_dict() for msg in history_messages]

        think: Union[ChatCompletionMessage, str] = await self.agent_node.chat(message, tools=self.toolkit.param_list)

        # openai fc
        if isinstance(think, ChatCompletionMessage) and think.tool_calls:
            think.tool_calls = think.tool_calls[:1]  # forbidden multiple tool call parallel
            todos = []
            for call_tool in think.tool_calls:
                todo = self.toolkit.tools.get(call_tool.function.name)
                todo_args = call_tool.function.arguments if call_tool.function.arguments else {}
                todo_args = json.loads(todo_args) if isinstance(todo_args, str) else todo_args
                tool_call_id = call_tool.id
                self.tool_calls_one_round.append(tool_call_id)  # a queue storage multiple calls and counter i
                todos.append((todo, todo_args, tool_call_id))

            # TODO: multiple tools call for openai support
            call_message = ToolMessage(non_standard=think)
            await self.rc.memory.add_one(call_message)
            self.rc.todos = todos
            return True, ''
        # Final answer, not tool call
        elif isinstance(think, str):
            final_answer = await self.parse_final_answer(think)
            if final_answer == MessageTag.REFLECTION.val:
                fix_msg = prompt_setting.self_reflection_for_invalid_json.render(
                    INVALID_DATA=think,
                    KEYWORDS=MessageType.keys()
                )
                return self._correction(fix_msg)
            self.answer = AssistantMessage(
                content=final_answer,
                sender=self.name,
                receiver={MessageTag.ALL.val},
                # extend conversation rounds like tool call
                tool_calls_one_round=self.tool_calls_one_round,
            )
            return False, final_answer
        # ollama fc
        elif isinstance(think, OMessage) and think.tool_calls and all(isinstance(i, OMessage.ToolCall) for i in think.tool_calls):
            tool_calls: List[OMessage.ToolCall] = think.tool_calls[:1]
            todos = []
            for fc in tool_calls:
                todo = self.toolkit.tools.get(fc.function.name)
                todo_args = fc.function.arguments if fc.function.arguments else {}
                todos.append((todo, todo_args, -1))

            call_message = Message(non_standard=think)
            await self.rc.memory.add_one(call_message)
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
                final_answer = content.get('FINAL_ANSWER')
                in_process_answer = content.get('IN_PROCESS')
            except json.JSONDecodeError:
                # send to self, no publish, no action
                fix_msg = prompt_setting.self_reflection_for_invalid_json.render(INVALID_DATA=think)
                return self._correction(fix_msg)

            if final_answer:
                json_match = re.search(r'({.*})', message[-1]['content'], re.DOTALL)
                think_process = ''
                if json_match:
                    match_group = json_match.group()
                    if is_valid_json(match_group):
                        think_process = json.loads(match_group).get('think_process', '')
                self.answer = AssistantMessage(content=final_answer, sender=self.name)
                await self.rc.memory.add_one(self.answer)
                return False, json.dumps({'final_answer': final_answer, 'think_process': think_process}, ensure_ascii=False)
            elif in_process_answer:
                self.answer = AssistantMessage(content=in_process_answer, sender=self.name)
                # will publish message in multi-agent env, so there are no need add message to memory
                return False, in_process_answer
            else:
                fix_msg = f'Your returned json data does not have a "FINAL ANSWER" key. Please check you answer:\n{final_answer}'
                return self._correction(fix_msg)

        # unexpected think format
        else:
            err = f'Unexpected chat response: {type(think)}'
            lgr.error(err)
            raise RuntimeError(err)

    @staticmethod
    async def parse_final_answer(think: str) -> str:
        if is_valid_json(think):
            think = json.loads(think)
            if think.get('FINAL_ANSWER'):
                final_answer = think.get('FINAL_ANSWER')
                return final_answer
            else:
                return MessageTag.REFLECTION.val
        else:
            return MessageTag.REFLECTION.val

    async def _react(self) -> Optional[Message]:
        message = Message.from_any('no tools taken yet')
        for todo in self.rc.todos:
            # lgr.debug(f'{self} react `{todo[0].name}` with args {todo[1]}')
            run = partial(todo[0].run, llm=self.agent_node)
            try:
                resp = await run(**todo[1])
                if isinstance(resp, ToolResponse):
                    if resp.is_success():
                        resp = resp.info
                    else:
                        resp = resp.msg
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

    async def run(self, with_message: Optional[Union[str, Dict, Message]] = None, ignore_history: bool = False) -> Optional[Union[Message, str]]:
        if with_message:
            msg = Message.from_any(with_message)
            self.rc.buffer.put_one_msg(msg)

        self.rc.action_taken = 0
        resp = Message(content='No action taken yet', role=RoleType.SYSTEM)
        while self.rc.action_taken < self.rc.max_react_loop:
            perceive = await self._perceive()
            if not perceive:
                await self.publish_message()
                break
            todo, reply = await self._think()
            if not todo:
                if reply == 'self-correction':
                    continue
                # Storing the conversation turn is now handled automatically
                # in memory.add_one when the assistant's reply is published.
                await self.publish_message()
                return reply
            resp = await self._react()
            # lgr.debug(f'{self} react [{self.rc.action_taken}/{self.rc.max_react_loop}]')
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
        return f'{self.name}({self.role_type.val})'

    def __repr__(self):
        return self.__str__()


class McpRole(Role):

    conn_type: McpTransportMethod = McpTransportMethod.STDIO
    exit_stack: AsyncExitStack = Field(default_factory=AsyncExitStack, validate_default=True)
    session: Optional[ClientSession] = Field(default=None, description='Session used for communication.', validate_default=True)
    server_script: str = Field(default=str(root_dir() / 'puti' / 'mcpp' / 'server.py'), description='Server script')

    initialized: bool = False
    init_lock: asyncio.Lock = Field(default_factory=asyncio.Lock, exclude=True)

    async def _initialize_session(self):
        if self.session:
            return  # Already initialized
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
            module = importlib.import_module(f'puti.llm.tools.{module_name}')
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseTool) and obj is not BaseTool:
                    self.toolkit.add_tool(obj)

        # filter tools that server have
        resp = await self.session.list_tools()
        mcp_server_tools = {tool.name for tool in resp.tools}

        self.toolkit.intersection_with(mcp_server_tools, inplace=True)

    async def disconnect(self):
        if self.initialized and self.exit_stack:
            await self.exit_stack.aclose()
            self.session = None
            self.toolkit = Toolkit()
            self.initialized = False

    async def run(self, *args, **kwargs):
        await self._initialize()
        resp = await super().run(*args, **kwargs)
        return resp

    async def _initialize(self):
        if self.initialized:
            return
        async with self.init_lock:
            if self.initialized:
                return
            await self._initialize_session()
            await self._initialize_tools()
            self.initialized = True
