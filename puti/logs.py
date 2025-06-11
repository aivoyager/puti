"""
@Author: obstacle
@Time: 10/01/25 14:09
@Description:  
"""
import sys

from datetime import datetime
from loguru import logger as _logger
from puti.constant.base import PuTi

_print_level = 'DEBUG'
_logfile_level = 'DEBUG'

formatted_date = datetime.now().strftime("%Y%m%d")


class LoggerFactory(object):
    _instance = None
    loggers = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            obj = super(LoggerFactory, cls).__new__(cls, *args, **kwargs)
            cls._define_loggers()
            cls._instance = obj
        return cls._instance

    @classmethod
    def _define_loggers(cls, print_level=_print_level, logfile_level=_logfile_level):
        _logger.remove()
        _logger.add(sys.stderr, level=print_level, enqueue=True, backtrace=True, diagnose=True)
        _logger.level("OBSTACLES", no=38, color="<green>", icon="😋")

        name_default = 'default'
        _logger.add(
            str(PuTi.ROOT_DIR.val / 'logs' / name_default / f'{formatted_date}.txt'),
            filter=lambda record: record['extra'].get('name') == name_default,
            level=logfile_level,
            enqueue=True,
            backtrace=True,
            diagnose=True,
            colorize=True
        )
        cls.loggers[name_default] = _logger.bind(name=name_default)

        name_client = 'client'
        _logger.add(
            str(PuTi.ROOT_DIR.val / 'test' / 'logs' / name_client / f'{formatted_date}.txt'),
            filter=lambda record: record['extra'].get('name') == name_client,
            level=logfile_level,
            enqueue=True,
            backtrace=True,
            diagnose=True,
            colorize=True
        )
        cls.loggers[name_client] = _logger.bind(name=name_client)

        name_client = 'llm'
        _logger.add(
            str(PuTi.ROOT_DIR.val / 'test' / 'logs' / name_client / f'{formatted_date}.txt'),
            filter=lambda record: record['extra'].get('name') == name_client,
            level=logfile_level,
            enqueue=True,
            backtrace=True,
            diagnose=True,
            colorize=True
        )
        cls.loggers[name_client] = _logger.bind(name=name_client)

        return cls

    @property
    def default(self):
        return self.loggers['default']

    @property
    def client(self):
        return self.loggers['client']

    @property
    def llm(self):
        return self.loggers['llm']


logger_factory = LoggerFactory()
