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

from utils.path import root_dir
from abc import ABC
from llm.tools import BaseTool, ToolArgs
from pydantic import ConfigDict, Field
from typing import Optional, Literal, List
from core.resp import ToolResponse, Response
from constant.base import Resp


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

    def run(self, command: str, path: str, *args, **kwargs) -> ToolResponse:

        pass











