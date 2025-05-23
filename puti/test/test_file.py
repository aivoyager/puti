"""
@Author: obstacle
@Time: 13/01/25 15:30
@Description:  
"""
from utils import FileModel
from constant import VA

f = FileModel()


def test_read_file():
    rs = f.read_file(VA.ROOT_DIR.val / 'conf' / 'cookie_twitter.json')
    assert rs

    rs2 = f.read_file(VA.ROOT_DIR.val / 'conf' / 'conf.yaml')
    assert rs2