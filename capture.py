"""
@Author: obstacle
@Time: 16/01/25 11:30
@Description:  
"""
import asyncio
import traceback

from twikit.errors import Unauthorized
from httpx import ConnectTimeout, ConnectError
from inspect import iscoroutinefunction
from typing import Union, Dict
from pydantic import BaseModel, ConfigDict
from logs import logger_factory
from utils.common import get_structured_exception
from core.resp import Response
from constant.base import Resp


lgr = logger_factory.default


class Capture(BaseModel):
    """ exception capture """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    exe: Exception = None
    desc: str = None
    max_retries: int = 1

    def invoke(self, func, *args, **kwargs) -> Response:
        if 'retries' in kwargs:
            retries = kwargs.pop('retries')
        else:
            retries = 0

        try:
            if iscoroutinefunction(func):
                try:
                    asyncio.get_event_loop()
                    if asyncio.get_event_loop().is_running():
                        rs = func(*args, **kwargs)
                    else:
                        rs = asyncio.run(func(*args, **kwargs))
                except RuntimeError:
                    rs = asyncio.run(func(*args, **kwargs))
            else:
                rs = func(*args, **kwargs)
        except Unauthorized as e:
            lgr.error(f'Unauthorized Error: {e}, check your credentials and account')
            structured_e = self._e_handled(e)
            return Response.default(code=Resp.UNAUTHORIZED_ERR.val, msg=Resp.UNAUTHORIZED_ERR.dsp, data=structured_e)
        except (ConnectError, ConnectTimeout) as e:
            lgr.log('OBSTACLES', 'Connect Timeout, come on, try again!')
            if retries < self.max_retries:
                return self.invoke(func, *args, retries=retries + 1, **kwargs)
            else:
                structured_e = self._e_handled(e)
                return Response.default(code=Resp.CP_ERR.val, msg=Resp.CP_ERR.dsp, data=structured_e)
        except ZeroDivisionError as e:
            structured_e = self._e_handled(e)
            return Response.default(code=Resp.CP_ERR.val, msg=Resp.CP_ERR.dsp, data=structured_e)
        except Exception as e:
            structured_e = self._e_handled(e)
            return Response.default(code=Resp.CP_ERR.val, msg=Resp.CP_ERR.dsp, data=structured_e)
        else:
            return Response.default(data=rs)

    def _e_handled(self, e: Exception) -> Union[str, Dict[str, str]]:
        desc = traceback.format_exc()
        structured_e = get_structured_exception(e)
        self.exe = e
        self.desc = f'{structured_e}\n {desc}'
        lgr.error(f'{structured_e}\n {desc}')
        return structured_e
