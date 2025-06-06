"""
@Author: obstacles
@Time:  2025-06-06 17:14
@Description:
"""
import os
from dotenv import load_dotenv


def test_load_config_from_env():
    """ A simple script to verify that the configuration is loaded correctly from a .env file. """
    # --- Step 1: Load environment variables from .env file ---
    print("Attempting to load environment variables from .env file...")
    load_dotenv()
    print("load_dotenv() executed.")
    print("-" * 20)

    # --- Step 2: Read the expected values from the environment ---
    # We read them *after* load_dotenv() to see what was loaded.
    expected_key = os.environ.get('OPENAI_API_KEY')
    expected_url = os.environ.get('OPENAI_BASE_URL')
    expected_model = os.environ.get('OPENAI_MODEL')

    print(f"Value for OPENAI_API_KEY in environment: {expected_key}")
    print(f"Value for OPENAI_BASE_URL in environment: {expected_url}")
    print(f"Value for OPENAI_MODEL in environment: {expected_model}")

    if not all([expected_key, expected_url, expected_model]):
        print("\n❌ Error: Not all required environment variables were found.")
        print(
            "Please ensure a .env file exists in the root directory and contains OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL.")
        exit(1)

    print("-" * 20)

    # --- Step 3: Import the bootstrap and config classes ---
    print("Importing bootstrap to trigger config patching...")
    import puti.bootstrap  # noqa: F401
    from puti.conf.llm_config import OpenaiConfig
    print("Bootstrap and config classes imported.")
    print("-" * 20)

    # --- Step 4: Instantiate the config and verify values ---
    print("Instantiating OpenaiConfig to read the final values...")
    openai_conf = OpenaiConfig()

    print(f"Loaded API Key from config: {openai_conf.API_KEY}")
    print(f"Loaded Base URL from config: {openai_conf.BASE_URL}")
    print(f"Loaded Model from config:   {openai_conf.MODEL}")
    print("-" * 20)

    # --- Step 5: Assertions to confirm the test passes ---
    print("Running assertions...")
    assert openai_conf.API_KEY == expected_key
    assert openai_conf.BASE_URL == expected_url
    assert openai_conf.MODEL == expected_model

    print("\n✅ Success! The configuration was correctly loaded from the .env file.")