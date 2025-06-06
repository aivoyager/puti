"""
@Author: obstacle
@Time: 12/01/25 21:31
@Description:  
"""
import pytest
import os

from puti.conf.llm_config import OpenaiConfig
from pathlib import Path
from unittest.mock import patch
from puti.utils.yaml_model import YamlModel
from puti.conf.config import Config
from puti.conf.client_config import TwitterConfig

MOCK_ROOT_DIR = Path("/mock/root")
MOCK_YAML_DATA = {
    "clients": [
        {"twitter": {"BEARER_TOKEN": "xxx", "API_KEY": "aaa"}}
    ]
}
MOCK_ENV_VARS = {
    "SOME_ENV_VAR": "value",
    "OPENAI_API_KEY": "test-api-key",
    "OPENAI_BASE_URL": "https://api.test.com/v1",
    "OPENAI_MODEL": "gpt-4"
}


# Mock ConstantBase.ROOT_DIR 和 YamlModel.read_yaml
@pytest.fixture
def mock_dependencies():
    # mock enum class
    with patch('puti.constant.base.Base', autospec=True) as MockEnum, \
            patch.object(YamlModel, "read_yaml", return_value=MOCK_YAML_DATA), \
            patch("os.environ", MOCK_ENV_VARS):
        yield
        # context


def test_config_create_obj_init(mock_dependencies):
    c = Config()
    assert c.cc
    assert c.file_model


def test_config_inherit_init():
    c = TwitterConfig()
    assert c


def test_llm_conf(mock_dependencies):
    """测试 LLM 配置是否正确从环境变量加载"""
    c = OpenaiConfig()
    # 验证环境变量是否正确加载
    assert c.API_KEY == "test-api-key", "API_KEY 未正确从环境变量加载"
    assert c.BASE_URL == "https://api.test.com/v1", "BASE_URL 未正确从环境变量加载"
    assert c.MODEL == "gpt-4", "MODEL 未正确从环境变量加载"
    
    # 验证其他配置项是否存在
    assert hasattr(c, 'MAX_TOKEN'), "MAX_TOKEN 配置项不存在"
    assert hasattr(c, 'TEMPERATURE'), "TEMPERATURE 配置项不存在"
    assert hasattr(c, 'STREAM'), "STREAM 配置项不存在"


def test_llm_conf_without_env_vars():
    """测试在没有环境变量的情况下配置加载"""
    with patch.dict(os.environ, {}, clear=True):
        c = OpenaiConfig()
        # 验证配置对象是否正确初始化
        assert c is not None, "配置对象创建失败"
        # 验证环境变量相关的配置项是否为空
        assert c.API_KEY is None or c.API_KEY == "", "API_KEY 应该为空"
        assert c.BASE_URL is None or c.BASE_URL == "", "BASE_URL 应该为空"
        assert c.MODEL is None or c.MODEL == "", "MODEL 应该为空"


def test_celery_conf():
    from puti.conf.celery_private_conf import CeleryPrivateConfig
    c = CeleryPrivateConfig()
    print('')


def test_mysql_config():
    from puti.conf.mysql_conf import MysqlConfig
    config = MysqlConfig()
    assert config.USERNAME is not None, "USERNAME 配置未加载"
    assert config.PASSWORD is not None, "PASSWORD 配置未加载"
    assert config.HOSTNAME is not None, "HOSTNAME 配置未加载"
    assert config.DB_NAME is not None, "DB_NAME 配置未加载"
    assert config.PORT is not None, "PORT 配置未加载"
    print(f"MysqlConfig: USERNAME={config.USERNAME}, HOSTNAME={config.HOSTNAME}, DB_NAME={config.DB_NAME}, PORT={config.PORT}")

