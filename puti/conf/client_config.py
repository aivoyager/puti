"""
@Author: obstacle
@Time: 14/01/25 13:52
@Description:  
"""
from typing import Optional, List
from puti.conf.config import Config
from puti.constant.client import Client
from puti.constant.base import Modules
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

    def generate_oauth2_authorize_url(self, redirect_uri: str, scope: str = "tweet.read tweet.write users.read offline.access", state: str = "state", code_challenge: str = "challenge", code_challenge_method: str = "plain") -> str:
        """
        构造 Twitter OAuth2 授权码流程的授权链接
        :param redirect_uri: 回调地址（需在 Twitter 开发者后台配置）
        :param scope: 授权范围，空格分隔
        :param state: 防 CSRF 攻击的随机字符串
        :param code_challenge: PKCE code_challenge
        :param code_challenge_method: code_challenge_method，推荐使用 S256
        :return: 授权链接
        """
        base_url = "https://twitter.com/i/oauth2/authorize"
        params = {
            "response_type": "code",
            "client_id": self.CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method
        }
        from urllib.parse import urlencode
        return f"{base_url}?{urlencode(params)}"


class LunarConfig(Config):
    HOST: Optional[str] = None
    API_KEY: Optional[str] = None
    HEADERS: Optional[dict] = None
    ENDPOINT: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        field = self.__annotations__.keys()
        conf = self._subconfig_init(module=Modules.CLIENT.val, client=Client.LUNAR.val)
        for i in field:
            if not getattr(self, i):
                setattr(self, i, conf.get(i, None))
        self._init_headers()

    def _init_headers(self):
        if not self.HEADERS:
            self.HEADERS = {'Authorization': 'Bearer {}'.format(self.API_KEY)}


class GoogleConfig(Config):
    GOOGLE_API_KEY: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        field = self.__annotations__.keys()
        conf = self._subconfig_init(module=Modules.CLIENT.val, client=Client.GOOGLE.val)
        for i in field:
            if not getattr(self, i):
                setattr(self, i, conf.get(i, None))
