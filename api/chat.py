"""
@Author: obstacles
@Time:  2025-04-09 16:25
@Description:  
"""
from typing import Optional

from fastapi import APIRouter, Request
from api import GetTweetsByNameRequest
from llm.roles.cz import CZ
from core.resp import Response
from pydantic import BaseModel


chat_router = APIRouter()


class GenerateCzTweetRequest(BaseModel):
    text: Optional[str] = ''


@chat_router.post('/generate_cz_tweet')
def generate_cz_tweet(request: GenerateCzTweetRequest):
    cz = CZ()
    resp = cz.cp.invoke(cz.run, request.text)
    return resp


@chat_router.get('/callback')
def callback():
    return "ok"
