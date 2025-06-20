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
import puti.bootstrap

from puti.core.resp import ToolResponse, ChatResponse
from functools import partial
from ollama._types import Message as OMessage
from puti.llm.prompts import promptt
from puti.llm import tools
from puti.llm.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator, field_validator, SerializeAsAny
from typing import Optional, List, Iterable, Literal, Set, Dict, Tuple, Type, Any, Union
from puti.constant.llm import RoleType, ChatState
from puti.logs import logger_factory
from puti.constant.llm import TOKEN_COSTS, MessageRouter
from asyncio import Queue, QueueEmpty
from puti.llm.nodes import LLMNode, OpenAINode
from puti.llm.messages import Message, ToolMessage, AssistantMessage, UserMessage, SystemMessage
from puti.llm.envs import Env
from puti.llm.memory import Memory
from puti.utils.common import any_to_str, is_valid_json
from puti.capture import Capture
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from contextlib import AsyncExitStack
from puti.utils.path import root_dir
from puti.constant.client import McpTransportMethod
from typing import Annotated, Dict, TypedDict, Any, Required, NotRequired, ClassVar, cast
from pydantic.fields import FieldInfo
from puti.llm.tools import Toolkit, ToolArgs
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from puti.constant.llm import MessageRouter, MessageType


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
    todos: List[Message] = Field(default=[], exclude=True, description='Message contains fc information')
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
    agent_node: Optional[LLMNode] = Field(
        default=None,
        description='LLM node, lazily initialized. Use `self.llm` to access it.'
    )
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
        self.rc.memory.llm = self.llm
        self.rc.memory.top_k = self.llm.conf.FAISS_SEARCH_TOP_K

    @model_validator(mode='after')
    def check_address(self):
        if not self.address:
            self.address = {f'{any_to_str(self)}.{self.name}'}
        return self  # return self for avoiding warning

    @property
    def llm(self) -> LLMNode:
        """Lazily initialize and return the LLM node."""
        if self.agent_node is None:
            # VITAL: This ensures the node is only created when first needed,
            # allowing the bootstrap process to load configs beforehand.
            self.agent_node = OpenAINode()
        return self.agent_node

    @property
    def sys_think_msg(self) -> Optional[Dict[str, str]]:
        if not self.rc.env:
            sys_single_agent = promptt.sys_single_agent.render(
                WORKING_DIRECTORY_PATH=self.rc.root,
                FINAL_ANSWER_KEYWORDS=MessageType.FINAL_ANSWER.val,
                IDENTITY=self.identity,
                NAME=self.name,
                GOAL=self.goal
            )
            think_msg = SystemMessage.from_any(self.role_definition + sys_single_agent).to_message_dict()
        else:
            sys_multi_agent = promptt.sys_multi_agent.render(
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
        """ publish `self.answer` """
        if not self.answer:
            return

        # For multi angent
        if self.rc.env:
            self.rc.env.publish_message(self.answer)
            await self.rc.memory.add_one(self.answer)  # this one won't be perceived
            self.answer = None
        # For single angent
        else:
            await self.rc.memory.add_one(self.answer, role=self)
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
        """If have new message to handle with"""
        news = self.rc.buffer.pop_all()
        history = [] if ignore_history else self.rc.memory.get()
        new_list = []

        for n in news:
            if (
                n.sender in self.rc.subscribe_sender
                or self.address & n.receiver
                or MessageRouter.ALL.val in n.receiver
            ):
                if n not in history:
                    new_list.append(n)
                    await self.rc.memory.add_one(n, role=self)
        self.rc.news = new_list

        return True if len(self.rc.news) > 0 else False

    async def _think(self) -> tuple[Annotated[bool, 'if call tool'], Annotated[Message, 'message to return']]:
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
                recent_contents.add(f"{self} responded: {msg.content}")

        filtered_relevant_history = [text for text in relevant_history if text not in recent_contents]

        # 5. Inject filtered relevant history into the system prompt.
        if filtered_relevant_history:
            context_str = "\n".join(filtered_relevant_history)
            enhanced_prompt = promptt.enhanced_memory.render(context_str=context_str)
            enhanced_prompt = base_system_prompt['content'] + enhanced_prompt
            base_system_prompt['content'] = enhanced_prompt

        # 7. Construct the final message list for the LLM.
        history_messages = recent_messages
        message = [base_system_prompt] + [msg.to_message_dict() for msg in history_messages]

        think: Any = await self.llm.chat(message, tools=self.toolkit.param_list)

        chat_response = await self.llm.parse_chat_result(resp=think, toolkit=self.toolkit)

        if chat_response.chat_state == ChatState.FINAL_ANSWER:
            self.answer = AssistantMessage(
                content=chat_response.msg,
                sender=self.name,
                receiver={MessageRouter.ALL.val},
            )
            return False, self.answer
        elif chat_response.chat_state == ChatState.IN_PROCESS_ANSWER:
            self.answer = AssistantMessage(
                content=chat_response.msg,
                sender=self.name,
                receiver={MessageRouter.ALL.val},
            )
            return False, self.answer
        elif chat_response.chat_state == ChatState.SELF_REFLECTION:
            reflection_msg = AssistantMessage(
                content=chat_response.msg,
                sender=self.name,
                receiver=self.address,
                self_reflection=True
            )
            self.rc.buffer.put_one_msg(reflection_msg)
            return False, reflection_msg
        elif chat_response.chat_state == ChatState.FC_CALL:
            if chat_response.tool_call_id:
                self.tool_calls_one_round.append(chat_response.tool_call_id)
            call_message = ToolMessage(non_standard=think)  # for call message, we add origin to accord with official request
            await self.rc.memory.add_one(call_message)

            call_info_message = ToolMessage(non_standard=chat_response)  #
            self.rc.todos.append(call_info_message)
            return True, call_info_message

    async def _react(self) -> Message:
        message = Message.from_any('no tools taken yet')
        for todo in self.rc.todos:
            chat_response: ChatResponse = todo.non_standard

            run = partial(chat_response.tool_to_call.run, llm=self.llm)
            try:
                resp = await run(**chat_response.tool_args)
                if isinstance(resp, ToolResponse):
                    if resp.is_success():
                        resp = resp.info
                    else:
                        resp = resp.msg
                resp = json.dumps(resp, ensure_ascii=False) if not isinstance(resp, str) else resp
            except Exception as e:
                message = Message(non_standard_dic={
                    'type': 'function_call_output',
                    'call_id': chat_response.tool_call_id,
                    'output': str(e)
                })
                message = Message(content=str(e), sender=self.name, role=RoleType.TOOL, tool_call_id=chat_response.tool_call_id)
            else:
                message = Message.from_any(resp, role=RoleType.TOOL, sender=self.name, tool_call_id=chat_response.tool_call_id)
            finally:
                self.rc.buffer.put_one_msg(message)
                self.rc.todos = []
                self.rc.action_taken += 1
                self.answer = message
        return message

    async def run(self, msg: Optional[Union[str, Dict, Message]] = None, ignore_history: bool = False, *args, **kwargs) -> Optional[Union[Message, str]]:
        if msg:
            msg = Message.from_any(msg)
            self.rc.buffer.put_one_msg(msg)

        self.rc.action_taken = 0
        resp = Message(content='No action taken yet', role=RoleType.SYSTEM)

        while self.rc.action_taken < self.rc.max_react_loop:
            perceive = await self._perceive()
            if not perceive:
                await self.publish_message()
                break

            todo, reply = await self._think()
            if not todo:  # if have tool to call
                if isinstance(reply, AssistantMessage) and reply.self_reflection:
                    continue  # in next round handle issue
                await self.publish_message()
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


class GraphRole(Role):
    """
    A specialized role designed specifically for use within a Graph workflow.
    This role is optimized for vertex-based execution in a graph context.
    """
    is_in_graph: bool = Field(default=True, description="Flag indicating this role is part of a graph")
    vertex_id: Optional[str] = Field(default=None, description="ID of the vertex this role is associated with")
    graph_context: Dict[str, Any] = Field(default_factory=dict, description="Shared context within the graph")
    
    async def run(
            self,
            msg: Optional[Union[str, Dict, Message]] = None,
            previous_result: Optional[Any] = None,
            *args, **kwargs
    ) -> Optional[Union[Message, str]]:
        """
        A specialized run method for graph-based execution that can handle
        results from previous vertices in the graph workflow.
        
        Args:
            msg: The message to process
            previous_result: The result from the previous vertex in the graph
            
        Returns:
            The response message
        """
        # If a previous result is provided, use it as the message
        if previous_result is not None and msg is None:
            msg = previous_result
            
        # Add graph context information to kwargs
        if self.graph_context:
            kwargs.update({"graph_context": self.graph_context})
            
        # Add vertex ID to kwargs
        if self.vertex_id:
            kwargs.update({"vertex_id": self.vertex_id})
            
        # Add action name and description if provided
        action_name = kwargs.pop("action_name", None)
        action_description = kwargs.pop("action_description", None)
        
        if action_name:
            kwargs.update({"action": {"name": action_name, "description": action_description}})
        
        return await super().run(msg=msg, *args, **kwargs)
        
    def set_vertex_id(self, vertex_id: str):
        """Set the vertex ID for this role."""
        self.vertex_id = vertex_id
        
    def set_graph_context(self, context: Dict[str, Any]):
        """Set the shared graph context for this role."""
        self.graph_context = context


class CZ(McpRole):
    name: str = 'cz or 赵长鹏 or changpeng zhao'

    def model_post_init(self, __context: Any) -> None:
        self.llm.conf.MODEL = 'gemini-2.5-pro-preview-03-25'

    async def run(self, text, *args, **kwargs):
        self.llm.conf.STREAM = False
        intention_prompt = """
        Determine the user's intention, whether they want to post or receive a tweet. 
        Only return 1 or 0. 1 indicates that the user wants you to give them a tweet; otherwise, it is 0.
        Here is user input: {}
        """.format(text)
        judge_rsp = await self.llm.chat([UserMessage.from_any(intention_prompt).to_message_dict()])
        lgr.debug(f'post tweet choice is {judge_rsp}')
        if judge_rsp == '1':
            resp = await super(CZ, self).run(text, *args, **kwargs)
