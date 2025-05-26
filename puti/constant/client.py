"""
@Author: obstacles
@Time:  2025-03-04 14:14
@Description:  
"""
from puti.constant.base import Base


class LoginMethod(Base):
    COOKIE = ('cookie', 'Recommend for this')
    ACCOUNT = ('account', 'May lock account, not recommend')


class Client(Base):
    TWITTER = ('twitter', 'twitter client')
    WECHAT = ('wechat', 'wechat client')
    LUNAR = ('lunar', 'lunar client')
    GOOGLE = ('google', 'google client')


class TwikitSearchMethod(Base):
    TOP = ('Top', 'top search method')
    LATEST = ('Latest', 'latest search method')
    MEDIA = ('Media', 'media search method')


class McpTransportMethod(Base):
    STDIO = ('stdio', 'stdio transport')
    SSE = ('sse', 'sse transport')
