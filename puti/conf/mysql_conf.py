"""
@Author: obstacles
@Time:  2025-05-16 10:36
@Description:  
"""
from puti.conf.config import Config
from puti.constant.utilities import Utilities
from puti.constant.base import Modules
from pydantic import ConfigDict


class MysqlConfig(Config):
    USERNAME: str = None
    PASSWORD: str = None
    HOSTNAME: str = None
    DB_NAME: str = None
    PORT: int = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        field = self.__annotations__.keys()
        conf = self._subconfig_init(module=Modules.UTILITIES.val, utilities=Utilities.MYSQL.val)
        for i in field:
            if not getattr(self, i):
                setattr(self, i, conf.get(i, None))
