"""
@Author: obstacles
@Time:  2025-04-08 14:03
@Description:  
"""

from fastapi import APIRouter, Request
from api import GetTweetsByNameRequest

twikit_router = APIRouter()


@twikit_router.post('/get_tweets_by_name')
def get_tweets_by_name(data: GetTweetsByNameRequest, req: Request):
    twikit_client = req.app.state.twikit_client

    # req.app.

    pass
