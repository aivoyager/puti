"""
@Author: obstacle
@Time: 10/01/25 14:03
@Description:  
"""
import puti

from pathlib import Path
from loguru import logger


def root_dir():
    package_root = Path(puti.__file__).parent.parent
    for i in (".git", ".project_root", ".gitignore"):
        if (package_root / i).exists():
            break
        else:
            package_root = Path.cwd()
    logger.info(f'Package root set to {str(package_root)}')
    return package_root
