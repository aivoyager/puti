"""
@Author: obstacle
@Time: 14/01/25 13:52
@Description:  
"""
from typing import Optional, List
from conf.config import Config
from constant.client import Client
from constant.base import Modules
from pydantic import ConfigDict


class TwitterConfig(Config):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # basic authentication
    BEARER_TOKEN: Optional[str] = None
    API_KEY: Optional[str] = None
    API_SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN: Optional[str] = None
    ACCESS_TOKEN_SECRET: Optional[str] = None
    CLIENT_ID: Optional[str] = None
    CLIENT_SECRET: Optional[str] = None
    USER_NAME: Optional[str] = None
    PASSWORD: Optional[str] = None
    EMAIL: Optional[str] = None
    MY_ID: Optional[str] = None
    MY_NAME: Optional[str] = None

    # login cookies
    COOKIES: List[dict] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        field = self.__annotations__.keys()
        conf = self._subconfig_init(module=Modules.CLIENT.val, client=Client.TWITTER.val)
        for i in field:
            if not getattr(self, i):
                setattr(self, i, conf.get(i, None))
