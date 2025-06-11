"""
@Author: obstacle
@Time: 13/01/25 15:05
@Description:  
"""
import json
import inspect
import yaml

from pydantic import BaseModel, Field
from typing import List, Union, Literal, Optional
from pathlib import Path
from puti.logs import logger_factory
from puti.utils.common import has_decorator
from functools import wraps

lgr = logger_factory.default

__all__ = ["FileModel"]


def read_wrapper(func):
    """ Help with finding method in FileModel automatically """
    @wraps(func)
    def wrapper(*args, **kwargs):
        args = [i for i in args if isinstance(i, Path)]
        return func(*args, **kwargs)
    wrapper._is_read_wrapper = True
    return wrapper


class FileModel(BaseModel):
    """ File operating... """

    file_types: List[Literal['json', 'yaml']] = Field(
        default_factory=lambda: ['json', 'yaml'],
        validate_default=True,
        description="List of supported file types."
    )

    def read_file(self, file_path: Path):
        file_type = file_path.suffix.lstrip('.')
        if file_type not in self.file_types:
            err = f"File type {file_path.suffix} not supported."
            lgr.error(err)
            raise ValueError(err)
        if not file_path.exists():
            lgr.error(f"File {file_path} does not exist.")
            raise FileNotFoundError(f"File {file_path} does not exist.")
        methods = {name: func for name, func in inspect.getmembers(self, predicate=inspect.ismethod) if has_decorator(func, 'read_wrapper')}
        read_func = methods.get(f'_read_{file_type}')
        data = read_func(file_path)
        return data

    @read_wrapper
    @staticmethod
    def _read_json(file_path: Path, encoding: str = 'utf-8') -> Optional[Union[list, dict]]:
        with open(file_path, 'r', encoding=encoding) as f:
            return json.load(f)

    @read_wrapper
    @staticmethod
    def _read_yaml(file_path: Path, encoding: str = 'utf-8') -> Optional[Union[list, dict]]:
        with open(file_path, "r", encoding=encoding) as file:
            return yaml.safe_load(file)
