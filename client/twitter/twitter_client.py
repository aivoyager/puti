"""
@Author: obstacle
@Time: 10/01/25 11:21
@Description:  
"""
import datetime
import re
import pytz

from abc import ABC
from twikit import Tweet
from twikit.utils import Result
from httpx import ConnectTimeout
from typing import Optional, Type, Union, List
from pydantic import Field, ConfigDict, PrivateAttr
from twikit.client.client import Client as TwitterClient
from client.client import Client
from logs import logger_factory
from conf.client_config import TwitterConfig
from utils.common import parse_cookies, filter_fields
from constant.client import LoginMethod, TwikitSearchMethod
from constant.base import Resp
from client.client_resp import CliResp
from db.model.client.twitter import Mentions
from constant.client import Client as Cli


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
        self.db.tb_type = Mentions
        rs = await self.get_tweets_by_user(self.conf.MY_ID)
        for tweet in rs.data:
            info = {
                'text': re.sub(r' https://t\.co/\S+', '', tweet.text),
                'author_id': self.conf.MY_ID,
                'mention_id': tweet.id,
                'parent_id': None,
                'data_time': datetime.datetime.now(),
                'replied': False,
            }
            mentions = Mentions(**info)
            self.db.dbh.insert(mentions)
        lgr.info('Tweet saved successfully.')

    async def get_tweets_by_user(self, user_id: int) -> CliResp:
        # TODO: fixed param `count`
        tweets = await self._cli.get_user_tweets(user_id=str(user_id), tweet_type='Tweets', count=50)
        lgr.info('Tweets fetched by user successfully.')
        return CliResp.default(data=tweets)

    async def reply_to_tweet(self, text: str, media_path: list[str], tweet_id: int, author_id: int) -> CliResp:
        lgr.info(f"reply to tweet text :{text} author_id: {author_id} link = https://twitter.com/i/web/status/{tweet_id}")
        if author_id == self.conf.my_id:
            return CliResp(code=Resp.OK, msg="don't reply myself")
        rs = await self.post_tweet(text, media_path, reply_tweet_id=tweet_id)
        if rs.status != Resp.OK.val:
            return CliResp(code=Resp.POST_TWEET_ERR.val, msg=rs.message, cli=Cli.TWITTER)
        return CliResp.default(msg="reply success")

    async def post_tweet(self, text: str, image_path: Optional[List[str]] = None, reply_tweet_id: int = None) -> CliResp:
        self.db.tb_type = Mentions
        media_ids = []
        if image_path:
            for path in image_path:
                media_id = await self._cli.upload_media(path)
                lgr.info(f'Upload media {path}')
                media_ids.append(media_id)
        tweet = await self._cli.create_tweet(text, media_ids=media_ids, reply_to=reply_tweet_id)

        if tweet.is_translatable is not None:
            lgr.info(f"Post tweet text :{text} link = https://twitter.com/i/web/status/{reply_tweet_id}")
            info = {
                'text': text,
                'author_id': self.conf.MY_ID,
                'mention_id': tweet.id,
                'parent_id': str(reply_tweet_id),
                'data_time': datetime.datetime.now(),
                'replied': True,
            }
            mentions = Mentions(**info)
            self.db.dbh.insert(mentions)
        else:
            lgr.info(f"Post id is {tweet.id} translatable is None | link = https://twitter.com/i/web/status/{reply_tweet_id}")
            return CliResp(code=Resp.POST_TWEET_ERR.val,
                           msg=f"Post id is {tweet.id} translatable is None | link = https://twitter.com/i/web/status/{reply_tweet_id}",
                           cli=Cli.TWITTER)
        return CliResp(status=Resp.OK.val, msg=f"Post id is {tweet.id} transatable {tweet.is_translatable}", cli=Cli.TWITTER)

    async def get_mentions(
        self,
        start_time: datetime = None,
        reply_count: int = 100,
        search_method: TwikitSearchMethod = TwikitSearchMethod.LATEST
    ) -> CliResp:
        self.db.tb_type = Mentions
        tweets_replies = await self._cli.search_tweet(f'@{self.conf.MY_NAME}', search_method.val, count=reply_count)
        lgr.debug(tweets_replies)
        lgr.debug(self.conf.MY_NAME)
        all_replies = []

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
                all_replies.append(info)
                mentions = Mentions(**info)
                self.db.dbh.insert(mentions)

            if _tweet.next_cursor:
                try:
                    tweets_reply_next = await self._cli.search_tweet(
                        f'@{self.conf.MY_NAME}',
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
        self.conf = conf()

    def model_post_init(self, __context):
        if not self.conf:
            self.init_conf(conf=TwitterConfig)
        if self.login_flag is False:
            self.cp.invoke(self.login)
