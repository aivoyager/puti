"""
A simple script to verify that the configuration is loaded correctly
from environment variables.
"""
import os

from dotenv import load_dotenv

# --- Step 1: Set up mock environment variables for testing ---
# In a real scenario, these would be set in your shell (e.g., using 'export').
print("Setting up mock environment variables for testing...")
load_dotenv()

print("Mock environment variables set.")
print("-" * 20)


# --- Step 2: Import the bootstrap and config classes ---
# IMPORTANT: Importing bootstrap triggers the config patching logic.
print("Importing bootstrap to trigger config patching...")
import puti.bootstrap  # noqa: F401
from puti.conf.llm_config import OpenaiConfig
print("Bootstrap and config classes imported.")
print("-" * 20)


# --- Step 3: Instantiate the config and verify values ---
print("Instantiating OpenaiConfig to read the final values...")
openai_conf = OpenaiConfig()

print(f"Loaded API Key: {openai_conf.API_KEY}")
print(f"Loaded Base URL: {openai_conf.BASE_URL}")
print(f"Loaded Model:   {openai_conf.MODEL}")
print("-" * 20)


# --- Step 4: Assertions to confirm the test passes ---
print("Running assertions...")
assert openai_conf.API_KEY == 'key_from_environment'
assert openai_conf.BASE_URL == 'url_from_environment'
assert openai_conf.MODEL == 'model_from_environment'

print("\n✅ Success! The configuration was correctly loaded from environment variables.") 