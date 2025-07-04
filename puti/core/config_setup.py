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
from puti.constant.base import Pathh

# --- Configuration Constants ---
CONFIG_DIR = Pathh.CONFIG_DIR.val
CONFIG_FILE = Pathh.CONFIG_FILE.val
REQUIRED_VARS = ["OPENAI_API_KEY", "OPENAI_MODEL"]
OPTIONAL_VARS = ["OPENAI_BASE_URL"]
DEFAULTS = {
    "OPENAI_API_KEY": "YOUR_API_KEY_HERE",
    "OPENAI_BASE_URL": "",  # Default to empty so user can just press Enter
    "OPENAI_MODEL": "o4-mini",
}


def ensure_twikit_config_is_present():
    """
    Checks if the TWIKIT_COOKIE_PATH environment variable is set. If not,
    it prompts the user for the path and saves it to the .env file.
    """
    console = Console()
    load_dotenv(CONFIG_FILE)

    if os.getenv("TWIKIT_COOKIE_PATH"):
        return  # Configuration is present.

    console.print(Markdown("""
# 🍪 Twikit Configuration
We need the path to your `cookies.json` file for Twikit to work.
"""))

    cookie_path = ""
    while not cookie_path:
        cookie_path = questionary.text("📁 Please enter the path to your `cookies.json` file:").ask()
        if not cookie_path:
            console.print("[bold red]This field cannot be empty. Please provide a path.[/bold red]")
        elif not Path(cookie_path).is_file():
            console.print(f"[bold red]The file at `{cookie_path}` does not exist. Please check the path.[/bold red]")
            cookie_path = "" # Reset to re-trigger the loop

    # --- Save configuration to .env file ---
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    
    # Pre-check: If the .env file path exists as a directory, remove it.
    if Path(CONFIG_FILE).is_dir():
        Path(CONFIG_FILE).rmdir()
        console.print(f"Warning: Removed existing directory at `{CONFIG_FILE}` to create config file.", style="yellow")

    set_key(CONFIG_FILE, "TWIKIT_COOKIE_PATH", cookie_path)
    os.environ["TWIKIT_COOKIE_PATH"] = cookie_path  # Update current session's environment

    console.print(Markdown(f"✅ Twikit cookie path saved successfully to `{CONFIG_FILE}`."))


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
This information will be saved locally in a `.env` file in `{CONFIG_DIR}` for future use.
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
    if new_configs:
        # Ensure the ~/.puti directory exists before writing to it.
        Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)

        # Pre-check: If the .env file path exists as a directory, remove it.
        if Path(CONFIG_FILE).is_dir():
            Path(CONFIG_FILE).rmdir()
            console.print(f"Warning: Removed existing directory at `{CONFIG_FILE}` to create config file.", style="yellow")

        for key, value in new_configs.items():
            # Only save if the value is not None (it can be an empty string)
            if value is not None:
                set_key(CONFIG_FILE, key, str(value))
                os.environ[key] = str(value)  # Update the current session's environment

    console.print(Markdown(f"\n✅ Configuration saved successfully to `{CONFIG_FILE}`. Let's get started!"))
    console.print("-" * 20)
