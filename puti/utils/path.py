"""
@Author: obstacle
@Time: 10/01/25 14:03
@Description:  
"""
from pathlib import Path
import importlib.resources


def root_dir():
    package_root = Path(__file__).parent.parent.parent
    for i in (".git", ".project_root", ".gitignore"):
        if (package_root / i).exists():
            break
        else:
            package_root = Path.cwd()
    # logger.info(f'Package root set to {str(package_root)}')
    return package_root


def get_package_config_path() -> Path:
    """
    Gets the path to config.yaml within the installed puti package.
    This is the reliable way to find package data files.
    """
    return importlib.resources.files('puti') / 'conf' / 'config.yaml'
