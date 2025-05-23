"""
@Author: obstacle
@Time: 10/01/25 17:43
@Description:
"""
import os
import platform

from box import Box
from pydantic import BaseModel, ConfigDict, SerializeAsAny, Field, field_validator
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict
from pydantic.v1 import ConfigError
from utils.file_model import FileModel
from constant.base import PuTi, Modules
from utils.common import (check_module,
                          get_extra_config_path,
                          get_extra_config_dict,
                          get_mainly_config_dict)
from utils.path import root_dir
from constant.client import Client

__all__ = ['Config', 'conf']

system_name = platform.system()

conf_path = root_dir() / 'conf' / 'config.yaml'

# Later priority is higher, storing your secret key in somewhere else
DEFAULT_CONF_PATHS: List[Path] = [
    conf_path,
]

# Definition rule
# If configure here, sub model field be automatically loaded when the subclass conf is created
# key: {module}_{sub_name}_{FIELD in sub model}
EXTRA_CONF_PATHS: List[Tuple[str, Path]] = [
    # ('client_twitter_cookies',  Path('/Users/wangshuang/PycharmProjects/data/cookie_twitter.json'))
    # ('client_twitter_cookies',  Path('/Users/wangshuang/PycharmProjects/data/cookie_twiter2.json'))
]


class ConfigContext(BaseModel):
    """ Storaging real contextual information """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    env: Optional[Dict[str, str]] = Field(
        default_factory=dict, validate_default=True,
        description='environment variables'
    )
    module: Dict[str, Any] = Field(
        default_factory=lambda: defaultdict(dict), validate_default=True,
        description='different module configurations dict'
    )


class Config(BaseModel):
    """
        -> Make sure 'Config' class is the first in conf succession
            ```python
            from puti.conf.conf import Config
            class TwitterConfig(Config, other cls...)
            ```
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cc: ConfigContext = Field(
        default_factory=ConfigContext,
        validate_default=True,
        description='conf context'
    )
    file_model: SerializeAsAny[FileModel] = Field(
        default_factory=FileModel,
        validate_default=True,
        description='file operate'
    )

    @classmethod
    def _subconfig_init(cls, *, module, **kwargs):
        cc = Box(cls._default()).cc
        sub = cc.module.get(module, {})

        module_sub = kwargs.get(module, '')
        if module_sub == Client.TWITTER.val:
            mainly_conf = get_mainly_config_dict(configs=sub['mainly'], module_sub=module_sub)
            sub_conf = get_extra_config_dict(configs=sub['extra'], module=module, module_sub=module_sub)
            sub_conf.update(mainly_conf)
        else:
            if isinstance(sub, Dict):
                sub = sub['mainly']
            sub_conf = get_mainly_config_dict(configs=sub, module_sub=module_sub)
        return sub_conf

    @field_validator('cc', mode='before')
    @classmethod
    def config_context_init(cls, cc):
        cfgs = Box(cls._default())
        if not cc.module:
            cc = cfgs.cc
        return cc

    def model_post_init(self, __context):
        """
            -> Called when Config object instantiated
        """
        self._config_init()

    def _config_init(self):
        cfgs = Box(self._default())
        if not self.cc:
            self.cc = cfgs.cc
        if not self.file_model:
            self.file_model = cfgs.file_model

    @classmethod
    def _default(cls) -> Dict:
        """
            -> Get config_context field data
                -> Don't instantiate Config object in this method！

            -> cc structure format:
            {
                'env': {}
                'client': {
                    'mainly': [
                        {'twitter': {}, 'skipgram': {}, other clients defined in Client Constant...}
                    ],
                    'extra': {
                        'client_twitter_cookies': Any,  # '{module}_{client_name}_{FIELD in sub model}'
                        ...
                    }
                },
                'llm': {
                    'openai': {'field1': '', 'field2': ''...}
                }
                'other modules defined in Module Constant... ': ...
            }
        """
        default_conf = {}
        file_model = FileModel()
        cc = ConfigContext()

        # env
        env_configs = dict(os.environ)
        cc.env = env_configs

        # module
        read_confs = {}
        for path in DEFAULT_CONF_PATHS:
            read_conf = file_model.read_file(path)
            read_confs.update(read_conf)
        if not check_module(list(read_confs.keys())):
            raise ConfigError('Modules in conf file are not valid!')

        for module in read_confs:
            if module == Modules.CLIENT.val:
                module_dic = {'mainly': read_confs[module]}
                client_extra = {}
                module_conf_path = get_extra_config_path(configs=EXTRA_CONF_PATHS, module=module)
                for name, path in module_conf_path:
                    client_extra.update({name: file_model.read_file(path)})
                module_dic['extra'] = client_extra
                cc.module[module] = module_dic
            else:
                cc.module[module] = read_confs[module]

        default_conf['file_model'] = file_model
        default_conf['cc'] = cc
        return default_conf


conf = Config()
