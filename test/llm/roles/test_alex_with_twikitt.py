import pytest
import os
import time
from dotenv import load_dotenv
from puti.llm.roles.agents import Alex, Ethan
from puti.utils.common import print_green, print_blue


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alex_real_conversation_with_twikitt():
    """
    Integration test for a multi-turn conversation with the Alex agent using the real Twikitt tool.
    This test requires a .env file with OPENAI_API_KEY and TWIKIT_COOKIE_PATH set.
    """
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY") or not os.getenv("TWIKIT_COOKIE_PATH"):
        pytest.skip("Skipping integration test: OPENAI_API_KEY or TWIKIT_COOKIE_PATH not set in .env file.")

    # 1. Initialize the Alex agent
    ethan = Ethan()
    # Ensure the Twikitt client is not a mock from previous tests by resetting it.
    if 'twikit_tool' in ethan.toolkit.tools:
        ethan.toolkit.tools['twikit_tool'].client_manager._client = None

    conversation_history = []

    async def run_and_log(prompt):
        print_green(f"\\n--- User Prompt ---")
        print_green(prompt)
        response = await ethan.run(prompt)
        print_blue(f"--- Alex Response ---")
        print_blue(response)
        conversation_history.append({"prompt": prompt, "response": response})
        return response

    # --- Turn 1: Get my info ---
    await run_and_log("Can you get my Twitter profile information?")

    # --- Turn 2: Post a tweet ---
    tweet_content = f"Hello from a real integration test with my AI assistant Alex! Timestamp: {int(time.time())}"
    await run_and_log(f"Please post a tweet for me with the content: '{tweet_content}'")

    # --- Turn 3: Get my tweets (to find the one we just posted) ---
    response = await run_and_log("Can you show me my most recent tweet?")
    
    # Extract tweet ID from the response. This is brittle and depends on the LLM's output format.
    # A better way would be for the tool to return the ID, but for now, we parse it.
    tweet_id = None
    if "ID:" in response:
        try:
            # Assuming format "ID: 123456789"
            tweet_id = response.split("ID:")[1].split()[0].strip()
        except IndexError:
            pass
    
    print_green(f"Extracted Tweet ID: {tweet_id}")

    if tweet_id:
        # --- Turn 4: Like the tweet ---
        await run_and_log(f"Please like the tweet with ID {tweet_id}.")

        # --- Turn 5: Retweet the tweet ---
        await run_and_log(f"Now, please retweet the same tweet, ID {tweet_id}.")

        # --- Turn 6: Reply to the tweet ---
        reply_content = "This is a test reply from an integration test!"
        await run_and_log(f"Please reply to tweet {tweet_id} with: '{reply_content}'")
    else:
        print_green("Could not extract tweet ID, skipping like, retweet, and reply tests.")

    # --- Turn 7: Browse tweets ---
    await run_and_log("Please search for tweets containing '#python'.")

    # --- Turn 8: Get mentions ---
    await run_and_log("Can you check my latest mentions on Twitter?")

    print(f"\\n--- Alex Integration Test Conversation History ---")
    for turn in conversation_history:
        print(f"Prompt: {turn['prompt']}")
        print(f"Response: {turn['response']}\\n")
    print(f"------------------------------------------------")