"""
@Author: obstacles
@Time:  2025-03-04 14:08
@Description:  
"""
from llm.prompts import prompt_setting
from llm.actions import Action
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_validator, field_validator
from typing import Optional, List, Iterable, Literal
from constant.llm import RoleType
from logs import logger_factory
from typing import Dict, Tuple, Type, Any, Union
from constant.llm import TOKEN_COSTS, MessageRouter
from asyncio import Queue, QueueEmpty
from llm.nodes import LLMNode, OpenAINode
from llm.messages import Message
from llm.envs import Env
from llm.memory import Memory
from utils.common import any_to_str

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
    extra_demands: str = ''
    constraints: str = Field(
        default='utilize the same language as the user requirements for seamless communication',
        validate_default=True
    )
    address: set[str] = Field(default=set(), description='', validate_default=True)

    system_message: PrivateAttr(str) = Field(default=None, description='System message')
    actions: List[Action] = Field(default=[], validate_default=True, description='Action list can be performed')
    states: List[str] = Field(default=[], validate_default=True, description='Action to state number map')
    identity: RoleType = Field(default=RoleType.USER, description='Role identity')
    agent_node: LLMNode = Field(default_factory=OpenAINode, description='LLM node')
    rc: RoleContext = Field(default_factory=RoleContext)
    last_preserved: Message = None

    __hash__ = object.__hash__

    @model_validator(mode='after')
    def check_address(self):
        if not self.address:
            self.address = {f'{any_to_str(self)}.{self.name}'}

    @property
    def sys_msg(self) -> Optional[Dict[str, str]]:
        if not self.system_message:
            return {'role': RoleType.SYSTEM.val, 'content': self.role_definition}
        return {'role': RoleType.SYSTEM.val, 'content': self.system_message}

    @property
    def role_definition(self) -> str:
        name_exp = f'You name is {self.name}.' if self.name else ''
        sex_exp = f'You sex is {self.sex}.' if self.sex else ''
        age_exp = f'You age is {self.age}.' if self.age else ''
        job_exp = f'You job is {self.job}.' if self.job else ''
        skill_exp = f'You skill at {self.skill}.' if self.skill else ''
        goal_exp = f'You goal is {self.goal}.' if self.goal else ''
        personality_exp = f'You personality is {self.personality}.' if self.personality else ''
        constraints_exp = f'You constraints are {self.constraints}.' if self.constraints else ''
        extra_demands = f'Here are some extra demands on you: {self.extra_demands}.' if self.extra_demands else "You don't have extra demands."
        definition = name_exp + sex_exp + age_exp + job_exp + skill_exp + goal_exp + personality_exp + constraints_exp + extra_demands
        return definition

    def _reset(self):
        self.states = []
        self.actions = []

    def set_actions(self, actions: List[Union[Action, Type[Action]]]):
        for action in actions:
            act_obj = action()
            self.actions.append(act_obj)
            self.states.append(f'{len(self.actions) - 1}. {action}, action name: {act_obj.name}, action description: {act_obj.desc}\n')

    async def _perceive(self, ignore_history: bool = False):
        news = self.rc.buffer.pop_all()
        history = [] if ignore_history else self.rc.memory.get()
        self.rc.memory.add_batch(news)
        new_list = []
        for n in news:
            if n.sender in self.rc.subscribe_sender or self.address | n.receiver or MessageRouter.ALL.val in n.receiver:
                if n not in history:
                    new_list.append(n)
        self.rc.news = new_list
        if len(self.rc.news) == 0:
            lgr.debug(f'{self} no new messages, waiting.')
        else:
            new_texts = [f'{m.role.val}: {m.content[:20]}...' for m in self.rc.news]
            lgr.debug(f'{self} perceive {new_texts}.')

    async def _think(self) -> Optional[Union[bool, List[Dict]]]:
        prompt = prompt_setting.COMMON_STATE_TEMPLATE.format(
            history='\n'.join(['{}'.format(i) for i in self.rc.memory.get()]),
            states='\n'.join(self.states),
            n_states=len(self.states) - 1,
            previous_state=self.rc.state
        )
        message = {'role': RoleType.USER.val, 'content': prompt}
        choose_state = await self.agent_node.achat([self.sys_msg, message])
        if int(choose_state) == -1:
            lgr.debug(f"{self} think {'he' if self.sex == 'male' else 'her'} is idle.")
            return False
        else:
            self.rc.state = int(choose_state)
            self.rc.todo = self.actions[self.rc.state]
            lgr.debug(f"{self} think {'he' if self.sex == 'male' else 'her'} will do {self.rc.todo}.")
            return True

    async def _react(self) -> Optional[Message]:
        messages = [self.sys_msg] + self.rc.memory.to_dict()
        resp = await self.rc.todo.run(messages, llm=self.agent_node)
        resp_msg = Message(content=resp, role=self.identity, cause_by=self.rc.todo, sender=self.name, reply_to=self.rc.memory.get()[-1].id)
        self.rc.memory.add_one(resp_msg)
        self.rc.action_taken += 1
        return resp_msg

    async def run(self, with_message: Optional[Union[str, Dict, Message]] = None, ignore_history: bool = False) -> Optional[Message]:
        if with_message:
            msg = Message.from_any(with_message)
            self.rc.buffer.put_one_msg(msg)

        await self._perceive()
        self.rc.action_taken = 0
        resp = Message(content='No action taken yet', role=RoleType.SYSTEM)
        while self.rc.action_taken < self.rc.max_react_loop:
            todo = await self._think()
            if not todo:
                break
            resp = await self._react()
        self.rc.state = -1
        self.rc.todo = None
        self.rc.env.publish_message(resp)
        return resp

    async def _get_corporate_prompt(self):
        prompt = ''
        if self.rc.env and self.rc.env.desc:
            all_roles = self.rc.env.members.keys()
            other_roles = ', '.join([r for r in all_roles if r != self.name])
            env_desc = f'You are in {self.rc.env.desc} with roles({other_roles})'
            prompt += env_desc
        return prompt

    def __str__(self):
        return f'{self.name}({self.identity.val})'

    def __repr__(self):
        return self.__str__()
