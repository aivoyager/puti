"""
@Author: obstacle
@Time: 10/01/25 18:18
@Description:  
"""
import traceback
import json
import random
import platform
import importlib

from typing import Dict, Iterable, Callable, List, Tuple, Any, Union
from collections import defaultdict
from constant.base import Modules
from logs import logger_factory
from pathlib import Path
from box import Box

lgr = logger_factory.default


def merge_dict(dicts: Iterable[Dict]) -> Dict:
    """
        -> Merge multiple dicts into one, with the latter dict overwriting the former
    """
    result = {}
    for dictionary in dicts:
        result.update(dictionary)
    return result


def has_decorator(func: Callable, decorator: str):
    """
        -> checkout out a func has the decorator with `_is_{decorator name}` attribute
    """
    if hasattr(func, f'_is_{decorator}') and getattr(func, f'_is_{decorator}') is True:
        return True
    return False


def check_module(vals: List[str]) -> bool:
    """
        -> Check if modules exist based on puti.constant.constant_base.Modules
    """
    module_set = {module.val for module in list(Modules)}
    for val in vals:
        if val not in module_set:
            return False
    not_conf = module_set - set(vals)
    lgr.warning(", ".join(map(str, not_conf)))
    return True


def get_extra_config_path(*, configs: List[Tuple[str, Path]], module: str) -> List[Tuple[str, Path]]:
    """
        -> get conf path base on module
    """
    config_path = []
    for name, path in configs:
        read_module = name.split('_')[0]
        if module == read_module:
            config_path.append((name, path))
    return config_path


def get_mainly_config_dict(*, configs: List, module_sub: str) -> Dict[str, Any]:
    """ Get target conf from a list """
    rs = {}
    for i in configs:
        key = next(iter(i))
        if key == module_sub:
            val = i.get(key)
            rs.update(val)
    return rs


def get_extra_config_dict(*, configs: Dict[str, Any], module: str, module_sub: str) -> Dict[str, Any]:
    rs = defaultdict(None)
    for i in configs:
        sp = i.split('_')
        if module == sp[0] and module_sub == sp[1]:
            rs[sp[2].upper()] = configs.get(i)
    return rs


def parse_cookies(cookies: list) -> dict:
    rs = {}
    for cookie_item in cookies:
        cookie_item = Box(cookie_item)
        rs[cookie_item.name] = cookie_item.value
    return rs


def filter_fields(
        all_fields: Dict[str, Any],
        fields: List[str],
        *,
        ignore_capital: bool = False,
        rename_fields: List[str] = list
) -> Dict[str, Any]:
    """
    Get fields from all_fields
    :param all_fields: all fields you want to filter
    :param fields: the fields you want to filter
    :param ignore_capital: ignore capital letters
    :param rename_fields: with same length as `fields`
    :return: filtered result
    """
    rs = {}
    fields_lowercase = [i.lower() for i in fields]
    for field in all_fields:

        if ignore_capital:
            field_lowercase = field.lower()
            if field_lowercase in fields_lowercase:
                idx = fields.index(field)
                if rename_fields:
                    rs[rename_fields[idx]] = all_fields[field]
                else:
                    rs[field] = all_fields[field]
        else:
            if field in fields:
                idx = fields.index(field)
                if rename_fields:
                    rs[rename_fields[idx]] = all_fields[field]
                else:
                    rs[field] = all_fields[field]
    return rs


def get_structured_exception(e: Exception, dumps=False) -> Union[str, Dict[str, str]]:
    tb = traceback.extract_tb(e.__traceback__)
    filename, lineno, func_name, text = tb[-1] if tb else ('<unknown>', 0, '<unknown>', '<unknown>')
    error_structured = {
        'error': str(e),
        'type': type(e).__name__,
        'file': filename,
        'line': lineno,
        'function': func_name,
        'text': text
    }
    if dumps:
        return json.dumps(error_structured, ensure_ascii=False)
    return error_structured


def generate_random_15_digit_number():
    return random.randint(10 ** 14, 10 ** 15 - 1)


def load_workflow(workflow_path):
    try:
        with open(workflow_path, 'r') as file:
            workflow = json.load(file)
            return json.dumps(workflow)
    except FileNotFoundError:
        lgr.e(f"The file {workflow_path} was not found.")
        return None
    except json.JSONDecodeError:
        lgr.e(f"The file {workflow_path} contains invalid JSON.")
        return None


def is_mac():
    return platform.system() == "Darwin"


def get_specific_parent(cls, target_cls):
    """获取指定的父类"""
    while cls and cls != object:
        if issubclass(cls, target_cls) and cls != target_cls:
            return target_cls
        cls = cls.__bases__[0] if cls.__bases__ else None
    return None


def get_class_name(cls) -> str:
    """Return class name"""
    return f"{cls.__module__}.{cls.__name__}"


def any_to_str(val: Any) -> str:
    """Return the class name or the class name of the object, or 'val' if it's a string type."""
    if isinstance(val, str):
        return val
    elif not callable(val):
        return get_class_name(type(val))
    else:
        return get_class_name(val)


def import_class(class_name: str, module_name: str) -> type:
    module = importlib.import_module(module_name)
    a_class = getattr(module, class_name)
    return a_class
