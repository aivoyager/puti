"""
@Author: obstacles
@Time:  2025-04-18 10:41
@Description:  
"""
import pandas as pd

from puti.utils.path import root_dir

filter_file = str(root_dir() / 'data' / 'cz_filtered.json')


def test_data_convert():
    df = pd.read_json(filter_file)
    tweets_chunk = df['text'].str.cat(sep='===')
    with open(root_dir() / 'data' / 'tweet_chunk.txt', 'w') as f:
        f.write(tweets_chunk)
        print('')


