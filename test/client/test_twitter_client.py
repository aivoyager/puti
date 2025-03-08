"""
@Author: obstacle
@Time: 14/01/25 10:44
@Description:  
"""
import asyncio
import datetime
import re
import csv

from logs import logger_factory
from client.twitter import TwikitClient
from constant import VA

lgr = logger_factory.client


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
        with open(str(VA.ROOT_DIR.val / 'data' / 'trump.txt'), "a") as f:
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


    with open(str(VA.ROOT_DIR.val / 'data' / 'trump.txt'), "a") as f:
        count = 1
        for tweet in rs:
            txt = tweet.__dict__['text']
            tt = re.sub(r'https://t\.co/\S+', '', txt)
            tt += '\n'
            f.write(f'{count} ===> {tt}')
            count += 1
    with open(str(VA.ROOT_DIR.val / 'data' / 'trump.csv'), "a", newline='') as f:
        writer = csv.writer(f)
        for tweet in rs:
            txt = tweet.__dict__['text']
            tt = re.sub(r'https://t\.co/\S+', '', txt)
            tt += '\n'
            writer.writerow([tt])
    print('')


