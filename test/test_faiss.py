"""
@Author: obstacles
@Time:  2025-04-07 18:06
@Description:  
"""
from db.faisss import FaissIndex
from utils.path import root_dir


def test_faiss_index():
    f = FaissIndex(
        from_file=root_dir() / 'data' / 'cz2.json',
        to_file=root_dir() / 'data' / 'cz2.index',
    )
    info = f.search('赵长鹏是谁')
    print('ok')
