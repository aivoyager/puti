"""
@Author: obstacles
@Time:  2025-05-09 18:13
@Description:  
"""
import json
import multiprocessing
import sys

from io import StringIO
from puti.utils.path import root_dir
from abc import ABC
from puti.llm.tools import BaseTool, ToolArgs
from pydantic import ConfigDict, Field
from typing import Optional
from puti.core.resp import ToolResponse, Response
from puti.constant.base import Resp
from puti.logs import logger_factory
lgr = logger_factory.llm


class PythonArgs(ToolArgs):
    code: str = Field(
        ...,
        description="The Python code to execute."
    )


class Python(BaseTool, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'python_execute'
    desc: str = """Executes Python code string. Note: Only print outputs are visible, function return values 
    are not captured. Use print statements to see results."""
    args: PythonArgs = None

    @staticmethod
    def _run_code(code: str, result: dict, safe_globals: dict) -> ToolResponse:
        original_stdout = sys.stdout
        try:
            output_buffer = StringIO()
            sys.stdout = output_buffer
            exec(code, safe_globals, safe_globals)  # global and local
            val = output_buffer.getvalue()
            result['observation'] = val
            result['success'] = True
            return ToolResponse(code=Resp.TOOL_OK.val, msg=Resp.TOOL_OK.dsp, data=val)
        except Exception as e:
            result['observation'] = str(e)
            result['success'] = False
            return ToolResponse(code=Resp.TOOL_FAIL.val, msg=str(e))
        finally:
            sys.stdout = original_stdout

    async def run(self, code: str, timeout: int = 5, *args, **kwargs) -> ToolResponse:
        lgr.debug(f'{self.name} using...')

        with multiprocessing.Manager() as manager:
            result = manager.dict({'observation': "", "success": False})

            # sandbox
            if isinstance(__builtins__, dict):
                safe_globals = {'__builtins__': __builtins__}
            else:
                safe_globals = {'__builtins__': __builtins__.__dict__.copy()}
            proc = multiprocessing.Process(
                target=self._run_code, args=(code, result, safe_globals)
            )
            proc.start()
            proc.join()

            if proc.is_alive():
                proc.terminate()
                proc.join(1)
                msg = f'{Resp.TOOL_TIMEOUT.dsp} after {timeout} seconds'
                return ToolResponse(code=Resp.TOOL_TIMEOUT.val, msg=msg)
            return ToolResponse(code=Resp.TOOL_OK.val, data=json.dumps(dict(result), ensure_ascii=False))






