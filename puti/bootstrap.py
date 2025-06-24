"""
@Author: obstacle
@Time: 2024-07-28 12:00
@Description: Bootstrapping script to patch config with environment variables.
"""
import warnings
import sys
import os
import atexit
import subprocess
import shutil
import platform
from typing import Optional

# warnings.filterwarnings("ignore", category=UserWarning, module='multiprocessing.resource_tracker')
# # warnings.filterwarnings("ignore")
# sys.stderr = open(os.devnull, "w")
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from puti.constant.base import Pathh

# --- Set up PUTI_DATA_PATH environment variable if not already set ---
if not os.environ.get('PUTI_DATA_PATH'):
    data_path = os.path.expanduser(Pathh.CONFIG_DIR.val)
    os.makedirs(data_path, exist_ok=True)
    os.environ['PUTI_DATA_PATH'] = data_path

# --- CRITICAL: Load .env file BEFORE any other module code runs ---
# This populates os.environ so that all subsequent imports and logic
# (especially `puti.conf.config`) see the correct environment values from the start.

dotenv_path = find_dotenv(Pathh.CONFIG_FILE.val)
if dotenv_path:
    load_dotenv(dotenv_path)

# Set a specific cache directory for tiktoken. This is good practice and can
# also help prevent some caching-related concurrency issues.
if "TIKTOKEN_CACHE_DIR" not in os.environ:
    # We create a dedicated cache directory within the user's home to avoid conflicts.
    tiktoken_cache_dir = Path.home() / ".puti_cache" / "tiktoken"
    tiktoken_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TIKTOKEN_CACHE_DIR"] = str(tiktoken_cache_dir)

# Set up logging directory
try:
    log_dir = Path(os.environ.get('PUTI_LOG_DIR', str(Path.home() / 'puti' / 'logs')))
    log_dir.mkdir(parents=True, exist_ok=True)
    os.environ['PUTI_LOG_DIR'] = str(log_dir)
except Exception as e:
    print(f"Warning: Could not set up log directory: {e}")


# Ensure configuration is present
def ensure_config():
    """Ensure configuration is present by importing and calling the function"""
    from puti.core.config_setup import ensure_config_is_present
    ensure_config_is_present()


# Call ensure_config function
ensure_config()

# Now, with the environment correctly set, we can import the config modules.
from box import Box
from puti.conf.config import conf, Config  # Import both the instance and the class


def _substitute_env_vars(data):
    """Recursively traverses the config and replaces placeholders."""
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = _substitute_env_vars(value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            data[i] = _substitute_env_vars(item)
    elif isinstance(data, str) and '${' in data and '}' in data:
        placeholder = data.strip()
        if placeholder.startswith('${') and placeholder.endswith('}'):
            env_var_name = placeholder[2:-1]
            return os.environ.get(env_var_name, '')
    return data


def patch_config_and_loader():
    """
    Patches the global config object with environment variables AND monkey-patches
    the Config._subconfig_init method to ensure all new config objects get the
    patched data correctly.
    """
    # 1. Patch the global `conf` object that was created on initial import.
    # This ensures the in-memory config is up-to-date with environment variables.
    if hasattr(conf, 'cc') and hasattr(conf.cc, 'module'):
        _substitute_env_vars(conf.cc.module)

    # 2. Define a new, much simpler _subconfig_init method.
    # This method directly reads from our already-patched global `conf` object,
    # completely bypassing the flawed original implementation.
    def new_subconfig_init(cls, *, module, **kwargs):
        # Find the name of the sub-module we need (e.g., 'openai', 'mysql')
        sub_module_name = next((v for k, v in kwargs.items()), None)

        if sub_module_name:
            # Get the list of configs for the parent module (e.g., 'llm')
            module_configs = conf.cc.module.get(module, [])
            if module_configs:
                for config_item in module_configs:
                    # Find the specific dictionary for our sub-module
                    if isinstance(config_item, dict) and sub_module_name in config_item:
                        # Return the patched sub-dictionary as a Box object
                        return Box(config_item[sub_module_name])

        # Return an empty config if nothing is found
        return Box({})

    # 3. Apply the monkey-patch to the Config class, replacing the original method.
    Config._subconfig_init = classmethod(new_subconfig_init)


# Run the patch logic as soon as this module is imported.
patch_config_and_loader()


def setup_dev_environment(project_dir: Optional[str] = None) -> bool:
    """
    Set up the development environment for Puti.
    
    This function performs the following tasks:
    1. Determines the project directory
    2. Creates and activates a virtual environment if it doesn't exist
    3. Upgrades pip
    4. Installs the package in development mode
    5. Provides usage instructions
    
    Args:
        project_dir: Optional path to the project directory. If None, tries to determine it.
        
    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        # Determine the project directory
        if project_dir is None:
            # Try to find the project directory
            current_file = Path(__file__).resolve()
            project_dir = current_file.parent.parent  # Go up one level from puti/bootstrap.py
        else:
            project_dir = Path(project_dir).resolve()

        print(f"Setting up Puti development environment in: {project_dir}")

        # Check if virtual environment exists, if not create it
        venv_dir = project_dir / "venv"
        if not venv_dir.exists():
            print(f"Creating virtual environment in {venv_dir}")
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

        # Determine the correct activation script based on platform
        if platform.system() == "Windows":
            activate_script = venv_dir / "Scripts" / "activate"
            python_path = venv_dir / "Scripts" / "python"
            pip_path = venv_dir / "Scripts" / "pip"
        else:
            activate_script = venv_dir / "bin" / "activate"
            python_path = venv_dir / "bin" / "python"
            pip_path = venv_dir / "bin" / "pip"

        # Set environment variables to use the virtual environment
        os.environ["VIRTUAL_ENV"] = str(venv_dir)
        os.environ["PATH"] = f"{os.path.dirname(python_path)}:{os.environ['PATH']}"

        # Upgrade pip
        print("Upgrading pip...")
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)

        # Install the package in development mode
        print("Installing/updating puti in development mode...")
        subprocess.run([str(pip_path), "install", "-e", str(project_dir)], check=True)

        # Print usage instructions
        print("\n\033[32mPuti environment is ready!\033[0m")
        print("You can now use the \033[1mputi\033[0m command.")
        print("\nExamples:")
        print("  puti scheduler list           # List all scheduled tasks")
        print("  puti scheduler create name \"0 12 * * *\" --topic \"AI News\"  # Create a task")
        print("  puti scheduler run 1          # Run a specific task")
        print("\nTo activate this environment in the future, run:")
        print(f"  source {activate_script}")
        print("")

        return True
    except Exception as e:
        print(f"Error setting up development environment: {e}")
        return False


# Clean up any temporary resources on exit
def cleanup_on_exit():
    """Clean up any temporary resources on exit."""
    # Placeholder for any cleanup tasks we might need
    pass


# Register the cleanup function to run on exit
atexit.register(cleanup_on_exit)


# Function to be called from command line scripts
def main():
    """
    Main entry point when called directly from command line.
    Sets up the development environment.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Set up Puti development environment")
    parser.add_argument("--dir", help="Project directory path (optional)")
    args = parser.parse_args()

    success = setup_dev_environment(args.dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
