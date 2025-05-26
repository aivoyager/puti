"""
@Author: obstacles
@Time:  2025-05-09 14:08
@Description:  
"""
from puti.conf.config import Config
from puti.constant.utilities import Utilities
from puti.constant.base import Modules
from pydantic import ConfigDict


class CeleryPrivateConfig(Config):

    BROKER_URL: str = None
    RESULT_BACKEND_URL: str = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        field = self.__annotations__.keys()
        conf = self._subconfig_init(module=Modules.UTILITIES.val, utilities=Utilities.CELERY.val)
        for i in field:
            if not getattr(self, i):
                setattr(self, i, conf.get(i, None))
