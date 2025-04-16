"""
@Author: obstacles
@Time:  2025-04-09 16:25
@Description:  
"""
from fastapi import APIRouter, Request
from api import GetTweetsByNameRequest
from llm.roles.cz import CZ
from core.resp import Response


chat_router = APIRouter()


@chat_router.post('/generate_cz_tweet')
def generate_cz_tweet():
    cz = CZ()
    resp = cz.cp.invoke(cz.run, 'generate a cz tweet')
    return resp
