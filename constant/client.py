"""
@Author: obstacles
@Time:  2025-03-04 14:14
@Description:  
"""
from constant.base import Base


class LoginMethod(Base):
    COOKIE = ('cookie', 'Recommend for this')
    ACCOUNT = ('account', 'May lock account, not recommend')


class Client(Base):
    TWITTER = ('twitter', 'twitter client')
    WECHAT = ('wechat', 'wechat client')


class TwikitSearchMethod(Base):
    TOP = ('Top', 'top search method')
    LATEST = ('Latest', 'latest search method')
    MEDIA = ('Media', 'media search method')
