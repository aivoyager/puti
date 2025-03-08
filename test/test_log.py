"""
@Author: obstacle
@Time: 16/01/25 15:58
@Description:  
"""
from logs import logger_factory


def test_lgr():
    lgr = logger_factory.default
    lgr.log('OBSTACLES', 'hi')
