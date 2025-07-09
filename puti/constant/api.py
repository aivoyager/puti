"""
@Author: obstacles
@Time:  2025-07-09 14:12
@Description:  
"""
from puti.constant.base import Base


class RequestMethod(Base):
    GET = ('GET', 'get method')
    POST = ('POST', 'post method')
    PUT = ('PUT', 'put method')
    DELETE = ('DELETE', 'delete method')
