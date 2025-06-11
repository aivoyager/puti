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
from puti.db.mysql_operator import MysqlOperator

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
        db = MysqlOperator()
        for tweet in rs.data:
            text = re.sub(r' https://t\.co/\S+', '', tweet.text)
            author_id = self.conf.MY_ID
            mention_id = tweet.id
            parent_id = None
            data_time = datetime.datetime.now()
            replied = False
            sql = """
                INSERT INTO twitter_mentions (text, author_id, mention_id, parent_id, data_time, replied)
                VALUES (%s, %s, %s, %s, %s, %s)
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
        # if author_id == self.conf.my_id:
        #     return CliResp(code=Resp.OK, msg="don't reply myself")
        db = MysqlOperator()
        # 检查是否已回复
        sql_check = "SELECT replied FROM twitter_mentions WHERE mention_id = %s"
        result = db.fetchone(sql_check, (tweet_id,))
        if result is not None and result[0]:
            db.close()
            return CliResp(code=Resp.OK.val, msg="该推文已回复，无需重复操作")
        # 执行回复
        rs = await self.post_tweet(text, media_path, reply_tweet_id=tweet_id)
        if rs.code != Resp.OK.val:
            db.close()
            return CliResp(code=Resp.POST_TWEET_ERR.val, msg=rs.message, cli=Cli.TWITTER)
        # 回复成功，更新replied字段并保存记录
        sql_update = "UPDATE twitter_mentions SET replied = TRUE WHERE mention_id = %s"
        db.update(sql_update, (tweet_id,))
        # 如需保存回复记录，可在此插入新记录（如业务需要）
        db.close()
        return CliResp.default(msg="reply success")

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
            replied = True
            sql = """
                INSERT INTO twitter_mentions (text, author_id, mention_id, parent_id, data_time, replied)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (text, author_id, mention_id, parent_id, data_time, replied)
            db = MysqlOperator()
            db.insert(sql, params)
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
        db = MysqlOperator()

        async def _save_replies_recursion(_tweet: Union[Tweet, Result, List[Tweet]]):
            for i in _tweet:
                if start_time and start_time.replace(tzinfo=pytz.UTC) > i.created_at_datetime:
                    continue
                plaintext = re.sub(r'@\S+ ', '', i.full_text)
                replied = True if i.reply_count != 0 or i.id == self.conf.MY_ID else False
                info = {
                    'text': plaintext,
                    'author_id': i.user.id,
                    'mention_id': i.id,
                    'parent_id': i.in_reply_to,
                    'data_time': datetime.datetime.now(),
                    'replied': replied,
                }
                sql_existing = "SELECT mention_id FROM twitter_mentions WHERE mention_id IN %s"
                existing_ids = set(row[0] for row in db.fetchall(sql_existing, ([str(i.id) for i in _tweet],)))

                if i.id not in existing_ids:
                    sql = """
                        INSERT INTO twitter_mentions (text, author_id, mention_id, parent_id, data_time, replied)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    params = (plaintext, i.user.id, i.id, i.in_reply_to, datetime.datetime.now(), replied)
                    db.insert(sql, params)

                all_replies.append(info)

            if _tweet.next_cursor:
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
