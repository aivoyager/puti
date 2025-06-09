"""
@Author: obstacle
@Time: 2024-07-28 12:00
@Description: Bootstrapping script to patch config with environment variables.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# --- CRITICAL: Load .env file BEFORE any other module code runs ---
# This populates os.environ so that all subsequent imports and logic
# (especially `puti.conf.config`) see the correct environment values from the start.
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)

# --- FIX for multiprocessing leaks on macOS (from tiktoken or other libs) ---
# This is a known robust fix for stubborn multiprocessing issues on macOS,
# often triggered by libraries like `tiktoken` or `numpy`. It tells the
# Objective-C runtime to be less strict about safety checks when a process
# forks, which can prevent hangs and resource leaks.
if sys.platform == "darwin":
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# Set a specific cache directory for tiktoken. This is good practice and can
# also help prevent some caching-related concurrency issues.
if "TIKTOKEN_CACHE_DIR" not in os.environ:
    # We create a dedicated cache directory within the user's home to avoid conflicts.
    tiktoken_cache_dir = Path.home() / ".puti_cache" / "tiktoken"
    tiktoken_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TIKTOKEN_CACHE_DIR"] = str(tiktoken_cache_dir)

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
