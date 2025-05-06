# -*- coding: utf-8 -*-
"""
x_api.py
Encapsulated API class for sending and replying to tweets
"""
import json
import requests

from typing import Optional, Literal, Type
from pydantic import ConfigDict, Field
from conf.client_config import TwitterConfig
from logs import logger_factory
from client.client import Client
from abc import ABC
from utils.path import root_dir

lgr = logger_factory.client


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
        """Get a valid access token, automatically refresh if expired"""
        import os
        import time
        token_file = str(root_dir() / 'data' / 'twitter_tokens.json')
        if not os.path.exists(token_file):
            lgr.error("No token file found. Please authorize first.")
            return None
        with open(token_file, "r") as f:
            token_data = json.load(f)
        current_time = int(time.time())
        expires_at = token_data.get("expires_at", 0)
        if current_time >= (expires_at - 300):
            lgr.info("Access token expired or will expire soon. Refreshing...")
            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                lgr.error("No refresh token available. Need to reauthorize.")
                return None
            new_tokens = self._do_refresh_token_exchange(refresh_token)
            if new_tokens:
                token_data = {
                    "access_token": new_tokens["access_token"],
                    "refresh_token": new_tokens.get("refresh_token", refresh_token),
                    "expires_at": int(time.time()) + new_tokens["expires_in"],
                    "scope": new_tokens["scope"]
                }
                with open(token_file, "w") as f:
                    json.dump(token_data, f)
                lgr.info("Token refreshed and saved successfully.")
                return token_data["access_token"]
            else:
                lgr.error("Failed to refresh token.")
                return None
        else:
            lgr.info("Using existing valid access token.")
            return token_data["access_token"]

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

    async def post_tweet(self, text: str) -> dict:
        self._refresh_headers()
        url = f"{self.base_url}/tweets"
        payload = {"text": text}
        resp = False
        for i in range(2):
            try:
                # try:
                resp = requests.post(url, headers=self.headers, json=payload)
                # except Exception as e:
                #     print(e)
                #     import traceback
                #     traceback.print_exc()
                lgr.debug(resp)
                if resp.status_code == 401 and i == 0:
                    self._refresh_headers()
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.Timeout:
                return {"error": "Request timed out", "status_code": getattr(resp, 'status_code', None)}
            except Exception as e:
                if isinstance(resp, bool) and resp is False:
                    return {"error": str(e), "status_code": 400}
                if hasattr(resp, 'status_code') and resp.status_code == 401 and i == 0:
                    self._refresh_headers()
                    continue
                return {"error": str(e), "status_code": getattr(resp, 'status_code', None)}

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
