"""
@Author: obstacles
@Time:  2025-07-10 15:36
@Description:  
"""
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
import asyncio
import uvicorn

app = FastAPI()


@app.get("/sse")
async def sse_endpoint():
    async def event_generator():
        for i in range(5):
            yield {"event": "message", "data": f"Hello {i}"}
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())

uvicorn.run(app, host="0.0.0.0", port=8000)