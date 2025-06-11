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

# --- Configuration Constants ---
CONFIG_FILE = str(root_dir() / '.env')
REQUIRED_VARS = ["OPENAI_API_KEY", "OPENAI_MODEL"]
OPTIONAL_VARS = ["OPENAI_BASE_URL"]
DEFAULTS = {
    "OPENAI_API_KEY": "YOUR_API_KEY_HERE",
    "OPENAI_BASE_URL": "",  # Default to empty so user can just press Enter
    "OPENAI_MODEL": "o4-mini",
}


def ensure_config_is_present():
    """
    Checks if the required environment variables are set. If not, it prompts
    the user for them and saves them to the .env file. It will also prompt
    for optional variables if they aren't set.
    """
    console = Console()
    load_dotenv(CONFIG_FILE)

    missing_required = [var for var in REQUIRED_VARS if not os.getenv(var)]
    missing_optional = [var for var in OPTIONAL_VARS if not os.getenv(var)]

    if not missing_required and not missing_optional:
        return  # All configurations are present.

    # --- Prompt user for missing configurations ---
    console.print(Markdown(f"""
# ⚙️ Welcome to Puti! Let's set up your OpenAI configuration.
This information will be saved locally in a `.env` file in `{Path(CONFIG_FILE).parent}` for future use.
"""))

    new_configs = {}
    questions = {
        "OPENAI_API_KEY": lambda: questionary.password("🔑 Please enter your OpenAI API Key:").ask(),
        "OPENAI_BASE_URL": lambda: questionary.text(
            "🌐 Enter the OpenAI API Base URL (optional, press Enter to skip):",
            default=DEFAULTS["OPENAI_BASE_URL"]
        ).ask(),
        "OPENAI_MODEL": lambda: questionary.text(
            "🤖 Enter the model name to use:",
            default=DEFAULTS["OPENAI_MODEL"]
        ).ask(),
    }

    # Prompt for required variables, ensuring they are not empty
    for var in missing_required:
        value = ""
        while not value:
            value = questions[var]()
            if not value:
                console.print("[bold red]This field cannot be empty. Please provide a value.[/bold red]")
        new_configs[var] = value

    # Prompt for optional variables, allowing them to be empty
    for var in missing_optional:
        value = questions[var]()
        new_configs[var] = value

    # --- Save configurations to .env file ---
    for key, value in new_configs.items():
        # Only save if the value is not None (it can be an empty string)
        if value is not None:
            set_key(CONFIG_FILE, key, str(value))
            os.environ[key] = str(value) # Update the current session's environment

    console.print(Markdown(f"\n✅ Configuration saved successfully to `{CONFIG_FILE}`. Let's get started!"))
    console.print("-" * 20) 