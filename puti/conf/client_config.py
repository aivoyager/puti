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
        Construct the authorization URL for the Twitter OAuth2 Authorization Code Flow.
        :param redirect_uri: Callback URL (needs to be configured in the Twitter developer backend).
        :param scope: Authorization scope, separated by spaces.
        :param state: A random string to prevent CSRF attacks.
        :param code_challenge: PKCE code_challenge.
        :param code_challenge_method: The code_challenge_method, S256 is recommended.
        :return: The authorization URL.
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
