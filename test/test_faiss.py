"""
@Author: obstacles
@Time:  2025-04-07 18:06
@Description:  
"""
from puti.db.faisss import FaissIndex
from puti.utils.path import root_dir


def test_faiss_index():
    f = FaissIndex(
        from_file=root_dir() / 'data' / 'cz_filtered.json',
        to_file=root_dir() / 'data' / 'cz_filtered.index',
    )
    info = f.search('我的愿景是什么')
    print('检索结果:', info)
