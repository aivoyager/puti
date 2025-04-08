"""
@Author: obstacle
@Time: 20/01/25 14:42
@Description:  
"""
from pydantic import BaseModel
from fastapi import Request


class GetTweetsByNameRequest(BaseModel):
    twitter_name: str
