"""
@Author: obstacle
@Time: 10/01/25 11:19
@Description:  
"""
from pydantic import ConfigDict
from typing import Dict, Union, Iterable
from puti.core.resp import Response
from puti.constant.client import Client
from puti.constant.base import Resp


class CliResp(Response):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cli: Client = None

    @classmethod
    def default(cls, code: int = 200, msg: str = Resp.OK.dsp, data: Union[Dict, Iterable] = None) -> 'CliResp':
        return CliResp(**{
            'code': code,
            'msg': msg,
            'cli': Client.TWITTER,
            'data': data,
        })

