"""
@Author: obstacle
@Time: 10/01/25 10:56
@Description:  
"""

from pydantic import Field, BaseModel, ConfigDict, SerializeAsAny
from abc import abstractmethod
from puti.conf.config import Config
from capture import Capture
from typing import Type
from puti.db import DBM
from puti.db.model.client.twitter import UserModel


class Client(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    conf: SerializeAsAny[Config] = None
    cp: SerializeAsAny[Capture] = Field(default_factory=Capture, validate_default=True, description='Capture exception')
    db: SerializeAsAny[DBM] = Field(default_factory=lambda: DBM(tb_t=UserModel), description='DBM object')

    @abstractmethod
    def login(self):
        ...

    @abstractmethod
    def logout(self):
        ...

    @abstractmethod
    def init_conf(self, conf: Type[Config]):
        ...
