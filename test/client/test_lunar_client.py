"""
@Author: obstacles
@Time:  2025-04-08 14:26
@Description:  
"""

from client.lunar.lunar_client import LunarClient
from conf.client_config import LunarConfig


def test_lunar_conf():
    c = LunarConfig()
    print(c.API_KEY)
    assert c.API_KEY
    assert c.HOST
    print('')


def test_lunar_client():
    c = LunarClient()
    resp = c.get_creator_info_by_name('cz_binance')
    print(resp.data.creator_id)
    print('')
