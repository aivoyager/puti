"""
@Author: obstacles
@Time:  2025-05-13 11:02
@Description:  
"""
import json
import os
import re
import asyncio
import shlex
import sys
import pty
from collections import defaultdict

from utils.path import root_dir
from abc import ABC
from llm.tools import BaseTool, ToolArgs
from pydantic import ConfigDict, Field, BaseModel
from typing import Optional, Literal, List, Union, DefaultDict
from core.resp import ToolResponse, Response
from constant.base import Resp
from pathlib import Path
from logs import logger_factory
from core.exce import ToolError

lgr = logger_factory.llm


class FileOperator(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    encoding: str = 'utf-8'

    async def read_file(self, path: Union[str, Path]) -> str:
        try:
            return Path(path).read_text(encoding=self.encoding)  # return entity file content
        except Exception as e:
            lgr.error(e)
            return str(e)

    async def write_file(self, path: Union[str, Path], context: str) -> None:
        try:
            Path(path).write_text(context, encoding=self.encoding)
        except Exception as e:
            lgr.error(e)

    @staticmethod
    async def is_directory(path: Union[str, Path]) -> bool:
        return Path(path).is_dir()

    @staticmethod
    async def exists(path: Union[str, Path]) -> bool:
        return Path(path).exists()

    @staticmethod
    async def run_command(cmd: str, timeout: Optional[float] = 120.0):
        process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return (
                process.returncode or 0, stdout.decode(), stderr.decode()
            )
        except asyncio.TimeoutError as err:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            raise TimeoutError(f"Command {cmd} timed out") from err


class FileArgs(ToolArgs):
    command: Literal['view', 'create', 'str_replace', 'insert', 'undo_edit'] = Field(
        ...,
        description='The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.'
    )
    path: str = Field(..., description='Absolute path to file or directory.')
    file_text: str = Field(
        default=None,
        description='Required parameter of `create` command, with the content of the file to be created.'
    )
    old_str: str = Field(
        default=None,
        description='Required parameter of `str_replace` command containing the string in `path` to replace.'
    )
    new_str: str = Field(
        default=None,
        description='Optional parameter of `str_replace` command containing the new string (if not given,'
                    ' no string will be added). Required parameter of `insert` command containing the string to insert.'
    )
    insert_line: int = Field(
        default=None,
        description='Required parameter of `insert` command. The `new_str` will be inserted AFTER the line'
                    ' `insert_line` of `path`.'
    )
    view_range: List[int] = Field(
        default=None,
        description='Optional parameter of `view` command when `path` points to a file. If none is given, the full '
                    'file is shown. If provided, the file will be shown in the indicated line number range, e.g. '
                    '[11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows '
                    'all lines from `start_line` to the end of the file.'
    )


class File(BaseTool, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    name: str = 'file_operation'
    desc: str = """Custom editing tool for viewing, creating and editing files
* State is persistent across command calls and discussions with the user
* If `path` is a file, `view` displays the result of applying `cat -n`.  If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The `create` command cannot be used if the specified `path` already exists as a file
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
* The `undo_edit` command will revert the last edit made to the file at `path`

Notes for using the `str_replace` command:
* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file.  Be mindful of whitespaces!
* If the `old_str` parameter is not unique in the file, the replacement will not be performed.  Make sure to include enough context in `old_str` to make it unique
* The `new_str` parameter should contain the edited lines that should replace the `old_str`"""
    args: FileArgs = None

    # TODO: can use sandbox
    f_op: FileOperator = FileOperator()

    max_response_len: int = 16000
    snippet_lines: int = 4
    expand_tabs: bool = True
    init_line: int = Field(default=1, description='first line number')
    truncated_message: str = (
        "<response clipped><NOTE>To save on context only part of this file has been shown to you. "
        "You should retry this tool after you have searched inside the file with `grep -n` "
        "in order to find the line numbers of what you are looking for.</NOTE>"
    )
    file_history: DefaultDict[Union[str, Path], List[str]] = defaultdict(list)

    async def run(self, command: str, path: str, *args, **kwargs) -> ToolResponse:
        view_range: Optional[List[int]] = kwargs.pop('view_range', None)
        file_text: Optional[str] = kwargs.pop('file_text', None)
        old_str: Optional[str] = kwargs.pop('old_str', None)

        await self.validate_path(command, Path(path))

        if command == 'view':
            resp = await self.view(path, view_range)
        elif command == 'create':
            if file_text is None:
                raise ToolError('The `file_text` parameter is required for the `create` command.')
            else:
                await self.f_op.write_file(path, file_text)
                self.file_history[path].append(file_text)
                resp = ToolResponse.success(f'File created successfully at: {path}')
        elif command == 'str_replace':
           if old_str is None:
               raise ToolError("Parameter `old_str` is required for command: str_replace")
           resp = await self.str_replace

        return ToolResponse()

    async def validate_path(self, command: str, path: Path) -> None:
        """ validate input path """
        if not path.is_absolute():
            raise ToolError(f'Path {path} must be a absolute path')

        if command != 'create':
            if not await self.f_op.exists(path):
                raise ToolError(f'Path {path} does not exist, please check')

            is_dir = await self.f_op.is_directory(path)
            if is_dir and command != 'view':
                raise ToolError(f'The path {path} is a directory and only the `view` command can be used on directories')

        elif command == 'create':
            exists = await self.f_op.exists(path)
            if exists:
                raise ToolError(f'Path {path} already exists, please check, '
                                f'Cannot overwrite files using command `create`.')

    async def _view_directory(self, path) -> ToolResponse:
        file_cmd = f'find {path} -maxdepth 2 -not -path "*/\\.*"'
        return_code, stdout, stderr = await self.f_op.run_command(file_cmd)
        if not stderr:
            stdout = (
                f"Here's the files and directories up to 2 levels deep in {path}, "
                f"excluding hidden items: \n{stdout}\n"
            )
        if stderr:
            return ToolResponse(code=Resp.TOOL_OK.val, data=stdout)
        else:
            return ToolResponse(code=Resp.TOOL_OK.val, msg=stderr)

    async def _view_file(self, path, view_range, expand_tabs: bool = True) -> ToolResponse:
        file_content = await self.f_op.read_file(path)

        if view_range:
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ToolError(f'Invalid view_range, must be a list of two integers, e.g. [1, 10]')

            file_lines = file_content.split('\n')
            n_lines_file = len(file_lines)
            self.init_line, final_line = view_range

            if self.init_line < 1 or self.init_line > n_lines_file:
                raise ToolError(
                    f'Invalid `view_range`: {view_range}. Its first element `{self.init_line}` should be '
                    f'within the range of lines of the file: {[1, n_lines_file]}'
                )
            if final_line > n_lines_file:
                raise ToolError(
                    f'Invalid `view_range`: {view_range}. Its second element `{final_line}` should be '
                    f'smaller than the number of lines in the file: `{n_lines_file}`'
                )
            if final_line != -1 and final_line < self.init_line:
                raise ToolError(
                    f'Invalid `view_range`: {view_range}. Its second element `{final_line}` should be '
                    f'larger or equal than its first `{self.init_line}`'
                )

            if final_line == -1:
                file_content = '\n'.join(file_lines[self.init_line - 1:])
            else:
                file_content = '\n'.join(file_lines[self.init_line - 1: final_line])

        # truncate
        if self.max_response_len and len(file_content) > self.max_response_len:
            file_content = file_content[:self.max_response_len] + self.truncated_message
        if expand_tabs:
            file_content = file_content.expandtabs()

        # add line number
        file_content = '\n'.join(
            [
                f'{i + self.init_line:6}\t{line}'  # format width 6, right alignment
                for i, line in enumerate(file_content.split('\n'))
            ]
        )

        # postprocess
        final_resp = (
            f"Here's the result of running `cat -n` on {path}:\n"
            + file_content
            + "\n"
        )
        return ToolResponse(data=final_resp)

    async def view(self, path: Union[str, Path], view_range: Optional[List[int]] = None) -> ToolResponse:
        """ view file / directory """
        is_dir = await self.f_op.is_directory(path)

        if is_dir:
            if view_range:
                raise ToolError(f'The `view_range` parameter is not allowed when `path` points to a directory.')
            return await self._view_directory(path)
        else:
            return await self._view_file(path, view_range)

    async def str_replace(self, path: Union[str, Path], old_str: str, new_str: Optional[str] = None):
        file_content = (await self.f_op.read_file(path)).expandtabs()
        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ''

        occurrences = file_content.count(old_str)
        if occurrences == 0:
            raise ToolError(f"No replacement was performed, old_str `{old_str}` did not appear verbatim in {path}.")
        elif occurrences > 1:
            file_content_lines = file_content.split('\n')
            lines = [
                idx + 1
                for idx, line in enumerate(file_content_lines)
                if old_str in line
            ]
            raise ToolError(
                f"No replacement was performed. Multiple occurrences of old_str `{old_str}` "
                f"in lines {lines}. Please ensure it is unique"
            )

        new_file_content = file_content.replace(old_str, new_str)

        await self.f_op.write_file(path, new_file_content)

        # save original
        self.file_history[path].append(file_content)

        replacement_line = file_content.split(old_str)[0].count('\n')
        start_line = max(0, replacement_line - self.snippet_lines)
        end_line = replacement_line + self.snippet_lines + new_str.count('\n')
        snippet = '\n'.join(new_file_content.split('\n')[start_line: end_line + 1])

        success_msg = f'The file {path} has been edited. '

        if self.max_response_len and len(snippet) > self.max_response_len:
            snippet = snippet[:self.max_response_len] + self.truncated_message
        if self.expand_tabs:
            snippet = snippet.expandtabs()

        # add line number
        snippet = '\n'.join(
            [
                f'{i + start_line + 1:6}\t{line}'  # format width 6, right alignment
                for i, line in enumerate(snippet.split('\n'))
            ]
        )

        # postprocess
        final_resp = (
            f"Here's the result of running `cat -n` on a snippet of {path}:\n"
            + snippet
            + "\n"
        )
