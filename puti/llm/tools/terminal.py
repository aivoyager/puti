import json
import os
import re
import asyncio
import shlex
import sys
import pty

from puti.utils.path import root_dir
from abc import ABC
from puti.llm.tools import BaseTool, ToolArgs
from pydantic import ConfigDict, Field
from typing import Optional
from puti.core.resp import ToolResponse, Response
from puti.constant.base import Resp
from puti.logs import logger_factory

lgr = logger_factory.llm


class TerminalArgs(ToolArgs):
    command: str = Field(
        ...,
        description="(required) The CLI command to execute. This should be valid for the current operating system. "
                    "Ensure the command is properly formatted and does not contain any harmful instructions."
    )


class Terminal(BaseTool, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'execute_command'
    desc: str = """Request to execute a CLI(Command-Line Interface) command on the system.
Use this when you need to perform system operations or run specific commands to accomplish any step in the user's task.
You must tailor your command to the user's system and provide a clear explanation of what the command does.
Prefer to execute complex CLI commands over creating executable scripts, as they are more flexible and easier to run.
Commands will be executed in the current working directory.
Note: You MUST append a `sleep 0.02` to the end of the command for commands that will complete in under 20ms, as this will circumvent a known issue with the terminal tool where it will sometimes not return the output when the command completes too quickly.
"""
    args: TerminalArgs = None

    lock: asyncio.Lock = asyncio.Lock()
    current_path: str = os.getcwd()
    process: Optional[asyncio.subprocess.Process] = None

    @staticmethod
    def _sanitize_command(command: str) -> str:
        """
        Sanitize the command to prevent malicious or harmful commands.
        """
        dangerous_commands = ['rm', 'sudo', 'shutdown', 'rebot']
        tips = 'Use of dangerous commands is restricted.'
        try:
            parts = shlex.split(command)
            if any(cmd in dangerous_commands for cmd in parts):
                raise ValueError(tips)
        except ValueError:
            if any(cmd in command for cmd in dangerous_commands):
                raise ValueError(tips)
        return command

    async def _handle_cd_command(self, command: str) -> ToolResponse:
        try:
            # len judge
            parts = shlex.split(command)
            if len(parts) < 2:
                new_path = os.path.expanduser('~')
            else:
                new_path = os.path.expanduser(parts[1])

            # relative path
            if not os.path.isabs(new_path):
                new_path = os.path.join(self.current_path, new_path)
            new_path = os.path.abspath(new_path)

            # cd
            if os.path.isdir(new_path):
                self.current_path = new_path
                text = f"Changed directory to {self.current_path}"
                return ToolResponse(code=Resp.TOOL_OK.val, msg=Resp.TOOL_OK.dsp, data=text)
            else:
                text = f"Directory {new_path} does not exist."
                return ToolResponse(code=Resp.TOOL_FAIL.val, msg=text)
        except Exception as e:
            return ToolResponse(code=Resp.TOOL_FAIL.val, msg=str(e))

    async def run(self, command: str, *args, **kwargs) -> ToolResponse:
        lgr.debug(f'{self.name} using...')

        commands = [cmd.strip() for cmd in command.split('&') if cmd.strip()]
        final_output = ToolResponse(code=Resp.TOOL_OK.val, msg='', data='')

        for cmd in commands:
            sanitized_cmd = self._sanitize_command(cmd)

            if sanitized_cmd.lstrip().startswith('cd '):
                result = await self._handle_cd_command(sanitized_cmd)
            else:
                async with self.lock:
                    try:
                        self.process = await asyncio.create_subprocess_shell(
                            sanitized_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            cwd=self.current_path
                        )
                        stdout, stderr = await self.process.communicate()
                        if stdout:
                            print(f"\033[35m{stdout.decode('utf-8')}\033[0m", end='')
                        if stderr:
                            print('\033[91m' + stderr.decode('utf-8') + '\033[0m', end='', file=sys.stderr)  # 红色打印
                        stdout = stdout.decode('utf-8').strip()
                        stderr = stderr.decode('utf-8').strip()
                        if stderr:
                            result = ToolResponse.fail(msg=stderr)
                        else:
                            result = ToolResponse.success(data=stdout)
                    except Exception as e:
                        result = ToolResponse.fail(msg=str(e))
                    finally:
                        self.process = None
            if result.is_success():
                final_output.data += (
                    (result.data + '\n') if result.data else result.data
                )
            if not result.is_success():
                final_output.msg += (
                    (result.msg + '\n') if result.msg else result.msg
                )
        # trailing newlines
        final_output.data = final_output.data.rstrip()
        final_output.msg = final_output.msg.rstrip()
        return final_output

    async def run_with_pty(self, command: str, *args, **kwargs) -> ToolResponse:
        """
        使用pty创建伪终端执行命令，捕获终端原始输出，避免其他日志干扰。
        """
        import pty
        import select
        import time
        commands = [cmd.strip() for cmd in command.split('&') if cmd.strip()]
        final_output = ToolResponse(code=Resp.TOOL_OK.val, msg='', data='')
        for cmd in commands:
            sanitized_cmd = self._sanitize_command(cmd)
            if sanitized_cmd.lstrip().startswith('cd '):
                result = await self._handle_cd_command(sanitized_cmd)
            else:
                async with self.lock:
                    try:
                        master_fd, slave_fd = pty.openpty()
                        proc = await asyncio.create_subprocess_shell(
                            sanitized_cmd,
                            stdin=slave_fd,
                            stdout=slave_fd,
                            stderr=slave_fd,
                            cwd=self.current_path
                        )
                        os.close(slave_fd)
                        output = b''
                        while True:
                            r, _, _ = select.select([master_fd], [], [], 0.1)
                            if master_fd in r:
                                try:
                                    data = os.read(master_fd, 1024)
                                    if not data:
                                        break
                                    output += data
                                except OSError:
                                    break
                            if proc.returncode is not None:
                                break
                            await asyncio.sleep(0.01)
                        await proc.wait()
                        os.close(master_fd)
                        out_str = output.decode('utf-8', errors='ignore').strip()
                        if proc.returncode != 0:
                            result = ToolResponse.fail(msg=out_str)
                        else:
                            result = ToolResponse.success(data=out_str)
                    except Exception as e:
                        result = ToolResponse.fail(msg=str(e))
            if result.data:
                final_output.data += (
                    (result.data + '\n') if result.data else result.data
                )
            if result.msg:
                final_output.msg += (
                    (result.msg + '\n') if result.msg else result.msg
                )
        final_output.data = final_output.data.rstrip()
        final_output.msg = final_output.msg.rstrip()
        return final_output


