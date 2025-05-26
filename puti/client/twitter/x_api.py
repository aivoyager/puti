# -*- coding: utf-8 -*-
"""
x_api.py
Encapsulated API class for sending and replying to tweets
"""
import json
import requests
import traceback
import redis
import time

from typing import Optional, Literal, Type
from pydantic import ConfigDict, Field
from puti.conf.client_config import TwitterConfig
from puti.conf.celery_private_conf import CeleryPrivateConfig
from logs import logger_factory
from puti.client.client import Client
from abc import ABC
from puti.utils.path import root_dir
from puti.constant.base import Resp
from puti.core.resp import Response

lgr = logger_factory.client
c = CeleryPrivateConfig()


class TwitterAPI(Client, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    headers: dict = None
    auth_type: Literal['oauth2'] = Field(default='oauth2', description='OAuth type, oauth2 user context')
    base_url: str = 'https://api.twitter.com/2'

    def model_post_init(self, __context):
        if not self.conf:
            self.init_conf(conf=TwitterConfig)
        if not self.headers:
            self.headers = {
                "Authorization": f"Bearer {self.conf.ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
    def login(self):
        pass
    
    def logout(self):
        pass

    def init_conf(self, conf: Type[TwitterConfig]):
        self.conf = conf()

    def get_valid_access_token(self):
        """获取有效的access token，如果过期则自动刷新，全部从redis操作"""
        redis_client = redis.StrictRedis.from_url(c.BROKER_URL)
        access_token = redis_client.get("tweet_token:twitter_access_token").decode()
        refresh_token = redis_client.get("tweet_token:twitter_refresh_token").decode()
        expires_at = redis_client.get("tweet_token:twitter_expires_at").decode()
        if expires_at is not None:
            try:
                expires_at = int(expires_at)
            except Exception:
                expires_at = 0
        else:
            expires_at = 0
        current_time = int(time.time())
        if not access_token or not refresh_token or not expires_at:
            lgr.error("Redis中未找到token信息，请先授权。")
            return None
        if current_time >= (expires_at - 300):
            lgr.info("Access token已过期或即将过期，正在刷新...")
            new_tokens = self._do_refresh_token_exchange(refresh_token)
            if new_tokens:
                access_token = new_tokens["access_token"]
                refresh_token = new_tokens.get("refresh_token", refresh_token)
                expires_in = new_tokens["expires_in"]
                expires_at = int(time.time()) + expires_in
                redis_client.set("tweet_token:twitter_access_token", access_token)
                redis_client.set("tweet_token:twitter_refresh_token", refresh_token)
                redis_client.set("tweet_token:twitter_expires_at", expires_at)
                lgr.info("Token已刷新并保存到redis。")
                return access_token
            else:
                lgr.error("刷新token失败。")
                return None
        else:
            lgr.info("使用redis中已有的有效access token。")
            return access_token

    def _do_refresh_token_exchange(self, refresh_token):
        """Use refresh_token to refresh access_token, return new token dict, return None if failed"""
        url = f"https://api.twitter.com/2/oauth2/token"
        data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.conf.CLIENT_ID,
        }
        try:
            resp = requests.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            lgr.error(f"Refresh token failed: {e}")
            return None

    def _refresh_headers(self):
        """Refresh access_token in headers"""
        access_token = self.get_valid_access_token()
        if access_token:
            self.headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

    async def post_tweet(self, text: str) -> Response:
        self._refresh_headers()
        url = f"{self.base_url}/tweets"
        payload = {"text": text}
        try:
            resp = requests.post(url, headers=self.headers, json=payload)
            lgr.debug(f'x post resp: {resp}')
            resp.raise_for_status()
            return Response(code=Resp.OK.val, msg=Resp.OK.dsp, data=resp.json())
        except requests.Timeout:
            return Response(code=Resp.REQUEST_TIMEOUT.val, msg=Resp.REQUEST_TIMEOUT.dsp)
        except Exception as e:
            dsp = f'{Resp.POST_TWEET_ERR.dsp}: {e}. {traceback.format_exc()}'
            return Response(code=Resp.POST_TWEET_ERR.val, msg=dsp)

    def reply_tweet(self, text: str, in_reply_to_status_id: str) -> dict:
        self._refresh_headers()
        url = f"{self.base_url}/tweets"
        payload = {
            "text": text,
            "reply": {"in_reply_to_tweet_id": in_reply_to_status_id}
        }
        for i in range(2):
            resp = requests.post(url, headers=self.headers, json=payload)
            if resp.status_code == 401 and i == 0:
                self._refresh_headers()
                continue
            try:
                return resp.json()
            except Exception as e:
                return {"error": str(e), "status_code": resp.status_code}

    def get_unreplied_mentions(self) -> list:
        """
        Query all unreplied mention tweets
        :return: List of unreplied tweets
        """
        self._refresh_headers()
        url = f"{self.base_url}/users/{self.conf.MY_ID}/mentions"
        resp = requests.get(url, headers=self.headers)
        try:
            mentions = resp.json().get("data", [])
        except Exception as e:
            return [{"error": str(e), "status_code": resp.status_code}]
        replied_ids = set()
        url_replies = f"{self.base_url}/users/{self.conf.MY_ID}/tweets"
        replies_resp = requests.get(url_replies, headers=self.headers)
        try:
            replies = replies_resp.json().get("data", [])
            for tweet in replies:
                if tweet.get("in_reply_to_user_id"):
                    replied_ids.add(tweet.get("in_reply_to_status_id"))
        except Exception:
            pass
        unreplied = [m for m in mentions if m["id"] not in replied_ids]
        return unreplied

    def get_my_id(self) -> str:
        """
        获取当前认证用户的ID
        :return: 用户ID字符串
        """
        self._refresh_headers()
        url = f"{self.base_url}/users/me"
        try:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()["data"]["id"]
        except Exception as e:
            lgr.error(f"获取用户ID失败: {e}")
            return ""
