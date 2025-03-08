"""
@Author: obstacle
@Time: 12/01/25 21:31
@Description:  
"""
import pytest

from conf import OpenaiConfig
from pathlib import Path
from unittest.mock import patch
from utils.yaml_model import YamlModel
from conf import Config
from conf import TwitterConfig

MOCK_ROOT_DIR = Path("/mock/root")
MOCK_YAML_DATA = {
    "clients": [
        {"twitter": {"BEARER_TOKEN": "xxx", "API_KEY": "aaa"}}
    ]
}
MOCK_ENV_VARS = {"SOME_ENV_VAR": "value"}


# Mock ConstantBase.ROOT_DIR 和 YamlModel.read_yaml
@pytest.fixture
def mock_dependencies():
    # mock enum class
    with patch('puti.constant.constant_base.ConstantBase', autospec=True) as MockEnum, \
            patch.object(YamlModel, "read_yaml", return_value=MOCK_YAML_DATA), \
            patch("os.environ", MOCK_ENV_VARS):
        yield


def test_config_create_obj_init():
    c = Config()
    assert c.cc
    assert c.file_model


def test_config_inherit_init():
    c = TwitterConfig()
    assert c


def test_llm_conf():
    c = OpenaiConfig()
    assert c.API_KEY is not None

