"""
@Author: obstacle
@Time: 13/01/25 15:30
@Description:  
"""
from puti.utils.file_model import FileModel
from puti.constant.base import root_dir

f = FileModel()


def test_read_file():
    rs = f.read_file(root_dir() / 'conf' / 'cookie_twitter.json')
    assert rs

    rs2 = f.read_file(root_dir() / 'conf' / 'conf.yaml')
    assert rs2