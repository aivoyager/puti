"""
@Author: obstacle
@Time: 2024-07-28 12:00
@Description: Bootstrapping script to patch config with environment variables.
"""
import os
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


def patch_config_and_monkey_patch_loader():
    """
    Patches the global config object with environment variables AND
    monkey-patches the Config._default method to prevent re-reading the unpatched file.
    """
    # 1. Patch the global conf object that was created on initial import.
    if hasattr(conf, 'cc') and hasattr(conf.cc, 'module'):
        _substitute_env_vars(conf.cc.module)

    # 2. Define a new _default method.
    # This new method will be used by any subsequent Config object instantiations.
    # It returns the data from the *already patched* global `conf` object,
    # instead of re-reading the original file from disk.
    def new_default(cls) -> dict:
        # The original _default returned a dict like {'file_model': ..., 'cc': ...}.
        # We replicate that structure using the patched `conf` object's data.
        return conf.model_dump()

    # 3. Apply the monkey-patch to the Config class.
    # From now on, any call to Config._default() will execute our new_default()
    Config._default = classmethod(new_default)


# Run the patch logic as soon as this module is imported.
patch_config_and_monkey_patch_loader()
