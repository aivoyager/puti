"""
@Author: obstacle
@Time: 14/01/25 10:44
@Description:  
"""
import asyncio
import datetime
import re
import csv
import json

from logs import logger_factory
from client.twitter.twitter_client import TwikitClient
from utils.path import root_dir

lgr = logger_factory.client


def test_get_someone_tweet():
    t = TwikitClient()
    print('ok')
    user_id = '902926941413453824'  # cz, get by lunar
    count = 1

    with open(str(root_dir() / 'data' / 'cz_replies.txt'), "a") as f:
        tweets = asyncio.run(t._cli.get_user_tweets(user_id, tweet_type='Replies', count=200))
        count = 1

        def save_recursion(twe):
            global count
            for i in twe:
                txt = i.__dict__['text']
                ii = re.sub(r'https://t\.co/\S+', '', txt)
                ii += '\n'
                f.write(f'{count} ===> {ii}')
                count += 1

            if twe.next_cursor:
                tweet_next = asyncio.run(
                    t._cli.get_user_tweets(user_id, count=200, cursor=twe.next_cursor, tweet_type='Replies'))
                if tweet_next:
                    save_recursion(tweet_next)

        save_recursion(tweets)
    print('ok')


def test_data_convert():
    with open(str(root_dir() / 'data' / 'cz_media.txt'), 'r') as f:
        lines = f.readlines()

    new = []
    sub_str = ''
    for line in lines:
        if ('===> \n' not in line) and (line != '\n') and (line != ' \n'):
            if re.match('\d+ ===> ', line):
                info = {'instruction': 'generate a cz tweet', 'response': sub_str}
                if sub_str:
                    new.append(info)
                sub_str = ''
                line = re.sub('\d+ ===> ', '', line)
                sub_str += line
            else:
                line = re.sub('\d+ ===> ', '', line)
                sub_str += line

    with open(str(root_dir() / 'data' / 'cz_media.json'), 'w') as f:
        json.dump(new, f, indent=4)


def test_data_convert_step2():
    # 读取原始文件
    with open(str(root_dir() / 'data' / 'cz_media.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 转换格式
    converted = [{"id": idx + 1, "text": item["response"]} for idx, item in enumerate(data)]

    # 写入新文件
    with open(str(root_dir() / 'data' / 'cz_media2.json'), 'w', encoding='utf-8') as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)


def test_data_convert_step2_length_strict():
    """ 长度限制 """
    with open(str(root_dir() / 'data' / ''
                                        '.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    converted = [{"id": idx + 1, "text": item["response"]} for idx, item in enumerate(data) if len(item["response"]) > 50]
    with open(str(root_dir() / 'data' / 'cz_media2_length_strict.json'), 'w', encoding='utf-8') as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)
    print('')


def test_merge():
    with open(str(root_dir() / 'data' / 'cz_media2_length_strict.json'), 'r', encoding='utf-8') as f:
        data1 = json.load(f)
    with open(str(root_dir() / 'data' / 'cz2.json'), 'r', encoding='utf-8') as f:
        data2 = json.load(f)
    combined = data1 + data2
    for idx, item in enumerate(combined, start=1):
        item['id'] = idx

    # 保存到新文件
    with open(str(root_dir() / 'data' / 'cz_combined.json'), 'w', encoding='utf-8') as f_out:
        json.dump(combined, f_out, ensure_ascii=False, indent=2)

def test_post_tweet():
    t = TwikitClient()
    rs = t.cp.invoke(t.post_tweet, 'Hi, this is obstacles', ['/Users/wangshuang/PycharmProjects/ws_algorithm/puti/puti/data/demo.png'], 1873694119337595083)
    rs = t.cp.invoke(t.post_tweet, 'Hi, this is obstacles', [], 1873694119337595083)
    rs = t.cp.invoke(t.post_tweet, 'hello hello')
    rs2 = t.cp.invoke(t.reply_to_tweet)
    rs3 = t.cp.invoke(t.save_my_tweet)
    rs4 = t.cp.invoke(t.get_tweets_by_user, 1815381118813876224)
    rs = t.cp.invoke(t.get_mentions, datetime.datetime(2025, 1, 15))
    rs = t.cp.invoke(t.get_mentions)

    rs = asyncio.run(t._cli.search_tweet('@Donald J. Trump', product='Latest'))
    rs2 = asyncio.run(t._cli.search_tweet('@realDonaldTrump', product='Latest'))
    rs3 = asyncio.run(t._cli.get_tweet_by_id('25073877'))
    rs = asyncio.run(t._cli.get_user_tweets('25073877', tweet_type='Tweets'))
    rs4 = asyncio.run(t._cli.get_user_following('1815381118813876224'))  # 25073877

    try:
        with open(str(root_dir() / 'data' / 'trump.txt'), "a") as f:
            tweets = asyncio.run(t._cli.get_user_tweets('25073877', tweet_type='Tweets', count=200))
            count = 1

            def save_recursion(twe):
                global count
                for i in twe:
                    txt = i.__dict__['text']
                    ii = re.sub(r'https://t\.co/\S+', '', txt)
                    ii += '\n'
                    f.write(f'{count} ===> {ii}')
                    count += 1

                if twe.next_cursor:
                    tweet_next = asyncio.run(t._cli.get_user_tweets('25073877', count=200, cursor=twe.next_cursor, tweet_type='Tweets'))
                    if tweet_next:
                        save_recursion(tweet_next)

            save_recursion(tweets)
            lgr.info('*' * 50)
    except Exception as e:
        lgr.error(e)

    with open(str(root_dir() / 'data' / 'trump.txt'), "a") as f:
        count = 1
        for tweet in rs:
            txt = tweet.__dict__['text']
            tt = re.sub(r'https://t\.co/\S+', '', txt)
            tt += '\n'
            f.write(f'{count} ===> {tt}')
            count += 1
    with open(str(root_dir() / 'data' / 'trump.csv'), "a", newline='') as f:
        writer = csv.writer(f)
        for tweet in rs:
            txt = tweet.__dict__['text']
            tt = re.sub(r'https://t\.co/\S+', '', txt)
            tt += '\n'
            writer.writerow([tt])
    print('')


