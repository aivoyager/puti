"""
Handles the initial configuration setup for Puti by checking for
a .env file and prompting the user for necessary credentials if they are missing.
"""
import os
import questionary
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from dotenv import load_dotenv, find_dotenv, set_key
from puti.utils.path import root_dir

import puti.bootstrap  # noqa: F401

# --- Constants ---
ENV_FILE_PATH = str(root_dir() / '.env')
REQUIRED_VARS = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]
DEFAULTS = {
    "OPENAI_BASE_URL": "https://api.openai.com/v1",
    "OPENAI_MODEL": "o4-mini",
}


def ensure_config_is_present():
    """
    Checks if the required environment variables are set. If not, it prompts
    the user for them and saves them to the .env file.
    """
    console = Console()
    load_dotenv(ENV_FILE_PATH)

    missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var)]

    if not missing_vars:
        return  # All configurations are present.

    # --- Prompt user for missing configurations ---
    console.print(Markdown(f"""
# ⚙️ Welcome to Puti! Let's set up your OpenAI configuration.
This information will be saved locally in a `.env` file in `{Path(ENV_FILE_PATH).parent}` for future use.
"""))

    new_configs = {}
    questions = {
        "OPENAI_API_KEY": lambda: questionary.password("🔑 Please enter your OpenAI API Key:").ask(),
        "OPENAI_BASE_URL": lambda: questionary.text(
            "🌐 Enter the OpenAI API Base URL:",
            default=DEFAULTS["OPENAI_BASE_URL"]
        ).ask(),
        "OPENAI_MODEL": lambda: questionary.text(
            "🤖 Enter the model name to use:",
            default=DEFAULTS["OPENAI_MODEL"]
        ).ask(),
    }

    for var in missing_vars:
        # Loop until a valid (non-empty) value is provided
        value = ""
        while not value:
            value = questions[var]()
            if not value:
                console.print("[bold red]This field cannot be empty. Please provide a value.[/bold red]")
        new_configs[var] = value

    # --- Save configurations to .env file ---
    for key, value in new_configs.items():
        set_key(ENV_FILE_PATH, key, value)
        os.environ[key] = value # Update the current session's environment

    console.print(Markdown(f"\n✅ Configuration saved successfully to `{ENV_FILE_PATH}`. Let's get started!"))
    console.print("-" * 20) 