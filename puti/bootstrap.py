"""
@Author: obstacle
@Time: 2024-07-28 12:00
@Description: Bootstrapping script to patch config with environment variables.
"""
import os
from puti.conf.config import conf


def _substitute_env_vars(data):
    """Recursively traverses the config and replaces placeholders."""
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = _substitute_env_vars(value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            data[i] = _substitute_env_vars(item)
    elif isinstance(data, str) and '${' in data and '}' in data:
        # Simple substitution for now, can be extended with regex for more complex cases
        placeholder = data.strip()
        if placeholder.startswith('${') and placeholder.endswith('}'):
            env_var_name = placeholder[2:-1]
            # Use the environment variable value, or an empty string if not found
            return os.environ.get(env_var_name, '')
    return data


def patch_config():
    """Patches the global config object with values from environment variables."""
    if hasattr(conf, 'cc') and hasattr(conf.cc, 'module'):
        _substitute_env_vars(conf.cc.module)


# Run the patch logic as soon as this module is imported.
patch_config()
