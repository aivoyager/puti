"""
@Author: obstacles
@Time:  2025-04-18 15:36
@Description:  
"""
import pandas as pd

from utils.path import root_dir
from llm.nodes import OpenAINode


def test_generate_question():
    filter_json_path = str(root_dir() / 'data' / 'cz_filtered.json')
    df = pd.read_json(filter_json_path)
    batch = 10
    for i in range(0, len(df), batch):
        batch = df.iloc[i: i + batch]
        tweets = df['text'].str.cat(sep='###')

    node = OpenAINode()
    resp = node.chat()
    print('')

