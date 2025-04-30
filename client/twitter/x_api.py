# -*- coding: utf-8 -*-
"""
x_api.py
封装推文发送与回复功能的API类
"""
import json
from typing import Optional
import requests
from typing import Optional
from conf.client_config import TwitterConfig
from requests_oauthlib import OAuth1Session, OAuth2Session
from logs import logger_factory

lgr = logger_factory.client


class TwitterAPI:
    def __init__(self, config: Optional[TwitterConfig] = None):
        self.config = config or TwitterConfig()
        self.base_url = "https://api.twitter.com/2"
        # 判断认证方式
        # if self.config.ACCESS_TOKEN and self.config.ACCESS_TOKEN_SECRET and self.config.API_KEY and self.config.API_SECRET_KEY:
        if False:
            # OAuth 1.0a 用户上下文
            self.auth_type = "oauth1"
            self.oauth = OAuth1Session(
                self.config.API_KEY,
                client_secret=self.config.API_SECRET_KEY,
                resource_owner_key=self.config.ACCESS_TOKEN,
                resource_owner_secret=self.config.ACCESS_TOKEN_SECRET
            )
        elif self.config.BEARER_TOKEN:
            # OAuth 2.0 Bearer Token（用户上下文或应用上下文）
            self.auth_type = "oauth2"
            self.headers = {
                "Authorization": f"Bearer {self.config.ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
        else:
            raise ValueError("Twitter API认证信息不完整，请检查配置。")

    def post_tweet(self, text: str) -> dict:
        """
        发送推文
        :param text: 推文内容
        :return: 推文发送结果
        """
        url = f"{self.base_url}/tweets"
        payload = {"text": text}
        try:
            resp = None
            if getattr(self, "auth_type", None) == "oauth1":
                resp = self.oauth.post(url, json=payload, timeout=10)
            else:
                lgr.debug('post tweet by oauth2')
                resp = requests.post(url, headers=self.headers, json=payload, timeout=10, verify=False)
                lgr.debug(resp)
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout:
            return {"error": "请求超时", "status_code": getattr(resp, 'status_code', None)}
        except Exception as e:
            return {"error": str(e), "status_code": getattr(resp, 'status_code', None)}

    def reply_tweet(self, text: str, in_reply_to_status_id: str) -> dict:
        """
        回复推文
        :param text: 回复内容
        :param in_reply_to_status_id: 被回复推文的ID
        :return: 回复结果
        """
        url = f"{self.base_url}/tweets"
        payload = {
            "text": text,
            "reply": {"in_reply_to_tweet_id": in_reply_to_status_id}
        }
        if getattr(self, "auth_type", None) == "oauth1":
            resp = self.oauth.post(url, json=payload)
        else:
            resp = requests.post(url, headers=self.headers, json=payload)
        try:
            return resp.json()
        except Exception as e:
            return {"error": str(e), "status_code": resp.status_code}

    def get_unreplied_mentions(self) -> list:
        """
        查询所有未回复的提及推文
        :return: 未回复推文的列表
        """
        url = f"{self.base_url}/users/{self.config.MY_ID}/mentions"
        if getattr(self, "auth_type", None) == "oauth1":
            resp = self.oauth.get(url)
        else:
            resp = requests.get(url, headers=self.headers)
        try:
            mentions = resp.json().get("data", [])
        except Exception as e:
            return [{"error": str(e), "status_code": resp.status_code}]
        replied_ids = set()
        url_replies = f"{self.base_url}/users/{self.config.MY_ID}/tweets"
        if getattr(self, "auth_type", None) == "oauth1":
            replies_resp = self.oauth.get(url_replies)
        else:
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
