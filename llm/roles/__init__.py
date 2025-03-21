"""
@Author: obstacles
@Time:  2025-03-04 14:08
@Description:  
"""
import json
import re

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


lgr = logger_factory.llm


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
    sex: Literal['male', 'female'] = 'male'
    age: int = ''
    job: str = ''
    skill: str = ''
    goal: str = ''
    personality: str = ''
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
    last_preserved: Message = None

    interested_actions: Set[Type[Action]] = Field(
        default=set(),
        description='1. Message trigger by interested action will always be received,'
                    '2. Our Tool Action will always be set up in Tool action Response'
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
        return {'role': RoleType.SYSTEM.val, 'content': self.role_definition + extra_demands}

    @property
    def role_definition(self) -> str:
        env = self._env_prompt
        name_exp = f'You name is {self.name}.' if self.name else ''
        sex_exp = f'You sex is {self.sex}.' if self.sex else ''
        age_exp = f'You age is {self.age}.' if self.age else ''
        job_exp = f'You job is {self.job}.' if self.job else ''
        skill_exp = f'You skill at {self.skill}.' if self.skill else ''
        goal_exp = f'You goal is {self.goal}.' if self.goal else ''
        personality_exp = f'You personality is {self.personality}.' if self.personality else ''
        constraints_exp = f'You constraints are {self.constraints}.' if self.constraints else ''
        other_exp = (f'Here are some instructions to help you make your choice of action: '
                     f'If the name of the sender of the message ends with intermediate,'
                     f' it is an intermediate action, otherwise it is a full action.')
        definition = env + name_exp + sex_exp + age_exp + job_exp + skill_exp + goal_exp + personality_exp + other_exp + constraints_exp
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
            states = f'{len(self.actions) - 1}. {act_obj.name}: {act_obj.desc}\n'
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
        prompt = (
            prompt_setting.COMMON_STATE_TEMPLATE
            .replace('{history}', '\n'.join(map(str, self.rc.memory.get())))
            .replace('{states}', ''.join(self.states))
            .replace('{n_states}', str(len(self.states) - 1))
            .replace('{previous_state}', str(self.rc.state))
            .replace('{intermediate_name}', f'{self.name}_intermediate')
        )

        # prompt = prompt_setting.COMMON_STATE_TEMPLATE.format(
        #     history='\n'.join(['{}'.format(i) for i in self.rc.memory.get()]),
        #     states=''.join(self.states),
        #     n_states=len(self.states) - 1,
        #     previous_state=self.rc.state
        # )
        message = {'role': RoleType.USER.val, 'content': prompt}
        think = await self.agent_node.achat([self.sys_think_msg, message])
        if isinstance(self.agent_node, OllamaNode) and 'deepseek-r1' in self.agent_node.conf.MODEL:
            pattern = r'\{"state":\s*\d+,\s*"arguments":\s*\{.*?\}\}'
            think = re.search(pattern, think, re.DOTALL)
            if think:
                think = think.group().lstrip('```json').rstrip('```')
        think = json.loads(think)
        choose_state = think.get('state')
        think_arguments = think.get('arguments')
        if int(choose_state) == -1:
            lgr.debug(f"{self} think {'he' if self.sex == 'male' else 'her'} is idle.")
            return False
        else:
            self.rc.state = int(choose_state)
            self.rc.todo = self.actions[self.rc.state]
            if self.rc.todo.__annotations__.get('args'):
                self.rc.todo.args = self.rc.todo.__annotations__['args'](**think_arguments)
            lgr.debug(f"{self} think {'he' if self.sex == 'male' else 'her'} will do {self.rc.todo}.")
            return True

    async def _react(self) -> Optional[Message]:
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
            if self.rc.action_taken == 1:
                print('')
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
