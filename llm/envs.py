"""
@Author: obstacles
@Time:  2025-03-10 17:20
@Description:  
"""

from pydantic import BaseModel, Field, ConfigDict, create_model, model_validator, PrivateAttr, SerializeAsAny, field_validator
from typing import Optional, List, Iterable, Literal
from typing import Dict, Tuple, Type, Any, Union
from uuid import uuid4


class Env(BaseModel):
    id: str = Field(default_factory=lambda: uuid4(), validate_default=True, description='Unique code of messages')
    desc: str = Field(default='', description='Description of env')
    messages: List[Dict] = None
    children_envs: List['Env'] = None
    parent_env: 'Env' = None
    members: Dict[str, set[str]] = Field(default=None, description='key is role name, value is role address')
