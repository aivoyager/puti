"""
@Author: obstacle
@Time: 10/01/25 11:21
@Description:  
"""
import pytz
import re
import datetime

from abc import ABC
from twikit import Tweet
from twikit.utils import Result
from httpx import ConnectTimeout
from typing import Optional, Type, Union, List, Literal
from pydantic import Field, ConfigDict, PrivateAttr
from twikit.client.client import Client as TwitterClient
from puti.logs import logger_factory
from puti.client.client import Client
from puti.conf.client_config import TwitterConfig
from puti.utils.common import parse_cookies, filter_fields
from puti.constant.client import LoginMethod, TwikitSearchMethod
from puti.constant.base import Resp
from puti.client.client_resp import CliResp
from puti.constant.client import Client as Cli
from puti.db.sqlite_operator import SqliteOperator

lgr = logger_factory.client


class TwikitClient(Client, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    login_flag: bool = Field(default=False, description='if already login')
    login_method: LoginMethod = Field(
        default=LoginMethod.COOKIE,
        description="Specifies the login method. Can be either 'cookie' or 'account'."
    )
    _cli: TwitterClient = PrivateAttr(default_factory=lambda: TwitterClient('en-US'))

    async def save_my_tweet(self) -> None:

        rs = await self.get_tweets_by_user(self.conf.MY_ID)
        db = SqliteOperator()
        for tweet in rs.data:
            text = re.sub(r' https://t\.co/\S+', '', tweet.text)
            author_id = self.conf.MY_ID
            mention_id = tweet.id
            parent_id = None
            data_time = datetime.datetime.now()
            replied = False
            sql = """
                INSERT OR IGNORE INTO twitter_mentions (text, author_id, mention_id, parent_id, data_time, replied)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (text, author_id, mention_id, parent_id, data_time, replied)
            db.insert(sql, params)
        db.close()
        lgr.info('Tweet saved successfully.')

    async def get_tweets_by_user(
            self,
            user_id: str,
            recursive: bool = False,
            tweet_type: Literal['Tweets', 'Replies', 'Media', 'Likes'] = 'Tweets',
            count: int = 50
    ) -> CliResp:
        all_tweets = []
        cursor = None

        while True:
            tweets_page = await self._cli.get_user_tweets(
                user_id=str(user_id),
                tweet_type=tweet_type,
                count=count,
                cursor=cursor
            )
            if tweets_page:
                all_tweets.extend(tweets_page)
                if recursive and tweets_page.next_cursor:
                    cursor = tweets_page.next_cursor
                else:
                    break  # Exit if not recursive or no more pages
            else:
                break  # Exit if no tweets are returned

        lgr.info(f'Tweets fetched for user {user_id} successfully. Total tweets: {len(all_tweets)}')
        return CliResp.default(data=all_tweets)

    async def reply_to_tweet(self, text: str, media_path: list[str], tweet_id: int, author_id: int = None) -> CliResp:
        lgr.info(
            f"reply to tweet text :{text} author_id: {author_id} link = https://twitter.com/i/web/status/{tweet_id}")
        db = SqliteOperator()
        try:
            # Check if it has been replied to
            sql_check = "SELECT replied FROM twitter_mentions WHERE mention_id = ?"
            result = db.fetchone(sql_check, (str(tweet_id),))
            
            # If the mention exists and has been replied to, do nothing.
            if result and result['replied']:
                return CliResp(code=Resp.OK.val, msg="This tweet has already been replied to, no need to repeat the operation.")

            # Execute the reply by calling post_tweet
            rs = await self.post_tweet(text, media_path, reply_tweet_id=tweet_id)
            if rs.code != Resp.OK.val:
                return CliResp(code=Resp.POST_TWEET_ERR.val, msg=rs.message, cli=Cli.TWITTER)

            # After successfully replying, update the original mention's status to replied=TRUE
            sql_update = "UPDATE twitter_mentions SET replied = 1 WHERE mention_id = ?"
            db.update(sql_update, (str(tweet_id),))

            return CliResp.default(msg="reply success")
        finally:
            db.close()

    async def post_tweet(self, text: str, image_path: Optional[List[str]] = None,
                         reply_tweet_id: int = None) -> CliResp:
        media_ids = []
        if image_path:
            for path in image_path:
                media_id = await self._cli.upload_media(path)
                lgr.info(f'Upload media {path}')
                media_ids.append(media_id)
        tweet = await self._cli.create_tweet(text, media_ids=media_ids, reply_to=reply_tweet_id)

        if tweet.is_translatable is not None:
            lgr.info(f"Post tweet text :{text} link = https://twitter.com/i/web/status/{reply_tweet_id}")
            author_id = self.conf.MY_ID
            mention_id = tweet.id
            parent_id = str(reply_tweet_id) if reply_tweet_id else None
            data_time = datetime.datetime.now()
            # 1. When creating/posting a tweet, save it with replied = False.
            replied = False
            sql = """
                INSERT OR IGNORE INTO twitter_mentions (text, author_id, mention_id, parent_id, data_time, replied)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (text, author_id, mention_id, parent_id, data_time, replied)
            db = SqliteOperator()
            try:
                db.insert(sql, params)
            finally:
                db.close()
        else:
            lgr.info(
                f"Post id is {tweet.id} translatable is None | link = https://twitter.com/i/web/status/{reply_tweet_id}")
            return CliResp(code=Resp.POST_TWEET_ERR.val,
                           msg=f"Post id is {tweet.id} translatable is None | link = https://twitter.com/i/web/status/{reply_tweet_id}",
                           )
        return CliResp(status=Resp.OK.val, msg=f"Post id is {tweet.id} transatable {tweet.is_translatable}")

    async def get_mentions(
            self,
            start_time: datetime = None,
            reply_count: int = 100,
            search_method: TwikitSearchMethod = TwikitSearchMethod.LATEST,
            query_name: Optional[str] = None,
    ) -> CliResp:
        if not query_name:
            query_name = self.conf.MY_NAME
        lgr.debug(query_name)
        tweets_replies = await self._cli.search_tweet(query=f'@{query_name}', product=search_method.val,
                                                      count=reply_count)
        lgr.debug(tweets_replies)
        all_replies = []
        db = SqliteOperator()

        async def _save_replies_recursion(_tweet: Union[Tweet, Result, List[Tweet]]):
            tweet_list = list(_tweet)
            if not tweet_list:
                return

            mention_ids = [str(i.id) for i in tweet_list]
            placeholders = ','.join('?' for _ in mention_ids)
            sql_existing = f"SELECT mention_id FROM twitter_mentions WHERE mention_id IN ({placeholders})"
            existing_ids_tuples = db.fetchall(sql_existing, mention_ids)
            existing_ids = {row['mention_id'] for row in existing_ids_tuples}


            for i in tweet_list:
                if start_time and start_time.replace(tzinfo=pytz.UTC) > i.created_at_datetime:
                    continue
                
                if str(i.id) in existing_ids:
                    continue

                plaintext = re.sub(r'@\S+ ', '', i.full_text)
                replied = True if i.reply_count != 0 or i.user.id == self.conf.MY_ID else False
                info = {
                    'text': plaintext,
                    'author_id': i.user.id,
                    'mention_id': i.id,
                    'parent_id': i.in_reply_to,
                    'data_time': datetime.datetime.now(),
                    'replied': replied,
                }
                
                sql = """
                    INSERT OR IGNORE INTO twitter_mentions (text, author_id, mention_id, parent_id, data_time, replied)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (plaintext, i.user.id, i.id, i.in_reply_to, datetime.datetime.now(), replied)
                db.insert(sql, params)

                all_replies.append(info)

            if hasattr(_tweet, 'next_cursor') and _tweet.next_cursor:
                try:
                    tweets_reply_next = await self._cli.search_tweet(
                        f'@{query_name}',
                        search_method.val,
                        count=reply_count,
                        cursor=_tweet.next_cursor
                    )
                except ConnectTimeout as e:
                    lgr.e(e)
                    raise e
                if tweets_reply_next:
                    await _save_replies_recursion(tweets_reply_next)

        await _save_replies_recursion(tweets_replies)
        db.close()
        lgr.debug(all_replies)
        lgr.info('Get user mentions Successfully!')
        return CliResp(data=all_replies)

    async def login(self):
        if self.login_method == LoginMethod.COOKIE:
            self._cli.set_cookies(cookies=parse_cookies(self.conf.COOKIES))
        else:
            auth_infos = filter_fields(
                all_fields=self.conf.model_dump(),
                fields=['MY_NAME', 'EMAIL', 'PASSWORD'],
                ignore_capital=True,
                rename_fields=['auth_info_1', 'auth_info_2', 'password']
            )
            await self._cli.login(**auth_infos)
        self.login_flag = True
        lgr.info(f'Login successful in TwitterClient via "{self.login_method.val}"!')

    async def logout(self):
        await self._cli.logout()
        lgr.info(f'Logout successful in TwitterClient!')

    def init_conf(self, conf: Type[TwitterConfig]):
        self.conf: TwitterConfig = conf()

    def model_post_init(self, __context):
        if not self.conf:
            self.init_conf(conf=TwitterConfig)
        if self.login_flag is False:
            self.cp.invoke(self.login)
