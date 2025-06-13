import pytest
import os
from dotenv import load_dotenv
from puti.llm.roles.agents import Vision
from puti.constant.base import Pathh
from puti.llm.messages import Message

import puti.bootstrap

# Load environment variables from the project's .env file
# to ensure the API key is available for the integration test.
load_dotenv(Pathh.CONFIG_FILE.val)

# This is an integration test and requires a valid OPENAI_API_KEY.
# It will be skipped if the key is not found (after attempting to load from .env).
requires_openai_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Test requires OPENAI_API_KEY, not found in environment or .env file."
)

# Use a real image from the project for the test

REAL_IMAGE_PATH = str(Pathh.ROOT_DIR.val / "docs" / "puti_alex.png")


@requires_openai_key
@pytest.mark.asyncio
async def test_vision_agent_real_run():
    """
    Tests the Vision agent with a real image and prompt, making an actual
    API call to a vision-capable model like gpt-4o.

    This test is an integration test and requires network access and a valid
    OpenAI API key. It will be skipped if the key is not set.
    """
    # Ensure the image exists before running the test
    assert os.path.exists(REAL_IMAGE_PATH), f"Test image not found at {REAL_IMAGE_PATH}"

    agent = Vision()
    prompt = "描述一下图片中内容"

    msg = Message.image(text=prompt, image_url=REAL_IMAGE_PATH)
    # Run the agent, which will make a real API call
    response = await agent.run(msg)

    # Assert that we get a meaningful, non-empty response string
    assert isinstance(response, str)
    assert len(response) > 5, "The response from the vision model should not be empty."

    print(f"\nVision Agent Response: {response}")
