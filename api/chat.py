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
def generate_cz_tweet(responses={
    200: {
        "description": "Tweet generation successful",
        "content": {
            "application/json": {
                "example": {
                    "message": "Tweet generated successfully",
                    "tweet": "RT @BinanceWallet: 🚀 Enjoy zero trading fees on all swaps in #Binance Wallet for the next 6 months! Start trading now! 🔥"
                }
            }
        }
    }
}):
    cz = CZ()
    resp = cz.cp.invoke(cz.run, 'generate a cz tweet')
    return resp
