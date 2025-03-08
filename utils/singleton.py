"""
@Author: obstacles
@Time:  2025-03-06 16:19
@Description:  
"""
from pydantic import BaseModel


def singleton(func):
    """
        llm = get_chat_openai('agent_chat')
        llm = get_chat_openai()
        get two different obj
    """
    instances = {}

    def wrapper(*args, **kwargs):
        frozen = set()
        frozen_args = []
        for k, v in kwargs.items():
            if isinstance(v, str) or isinstance(v, int) or isinstance(v, float):
                frozen.update({k: v})
            if isinstance(v, BaseModel):
                model_name = v.__class__.__name__
                for kk, vv in v.__dict__.items():
                    if isinstance(vv, str) or isinstance(vv, int) or isinstance(vv, float):
                        frozen.add(f'{model_name}_{kk}_{vv}')

        for i in args:
            if isinstance(i, str) or isinstance(i, int) or isinstance(i, float):
                frozen_args.append(i)
        key = (id(func), tuple(frozen_args), frozenset(frozen))
        if key not in instances:
            instances[key] = func(*args, **kwargs)
        return instances[key]

    return wrapper
