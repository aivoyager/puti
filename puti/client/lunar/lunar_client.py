"""
@Author: obstacles
@Time:  2025-04-08 14:18
@Description:  
"""
import re

from puti.client.client import Client
from abc import ABC
from typing import Type
from puti.conf.client_config import LunarConfig
from puti.utils.common import request_url
from box import Box


class LunarClient(Client, ABC):

    def get_creator_info_by_name(self, twitter_name: str) -> Box:
        url = self.conf.HOST + self.conf.ENDPOINT.format(name=twitter_name)
        resp = request_url(url=url, method='GET', headers=self.conf.HEADERS, verify=False)
        user_id = re.search('\d+', resp.data.creator_id).group()
        resp.data.twitter_id = user_id
        return resp

    def login(self):
        pass

    def logout(self):
        pass

    def init_conf(self, conf: Type[LunarConfig]):
        self.conf = conf()

    def model_post_init(self, __context):
        if not self.conf:
            self.init_conf(conf=LunarConfig)
