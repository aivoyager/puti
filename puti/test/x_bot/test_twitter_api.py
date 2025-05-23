import asyncio
import time
import unittest
import json
import time
import os
import redis
import requests

from utils.path import root_dir
from unittest.mock import patch, MagicMock
from client.twitter.x_api import TwitterAPI
from conf.client_config import TwitterConfig


class TestTwitterAPI(unittest.TestCase):
    def setUp(self):
        """为每个测试方法准备相同的初始环境，避免重复代码"""
        # self.api.conf = TwitterConfig()
        self.api = TwitterAPI()

    # 使用unittest.mock的patch装饰器来模拟requests.post方法，避免实际发送HTTP请求
    @patch('client.twitter.x_api.requests.post')
    def test_post_tweet(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'data': {'id': '123', 'text': 'hello'}}
        mock_post.return_value = mock_resp
        result = self.api.post_tweet('hello')
        self.assertIn('data', result)
        self.assertEqual(result['data']['text'], 'hello')

    @patch('client.twitter.x_api.requests.post')
    def test_reply_tweet(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'data': {'id': '456', 'text': 'reply'}}
        mock_post.return_value = mock_resp
        result = self.api.reply_tweet('reply', '789')
        self.assertIn('data', result)
        self.assertEqual(result['data']['text'], 'reply')

    @patch('client.twitter.x_api.requests.get')
    def test_get_unreplied_mentions(self, mock_get):
        # mock mentions
        mock_mentions_resp = MagicMock()
        mock_mentions_resp.json.return_value = {'data': [{'id': '1'}, {'id': '2'}]}
        # mock replies
        mock_replies_resp = MagicMock()
        mock_replies_resp.json.return_value = {'data': [{'in_reply_to_user_id': 'xxx', 'in_reply_to_status_id': '1'}]}
        # 当被测试代码中第一次调用 requests.get() 时，会返回列表中的第一个模拟响应 mock_mentions_resp
        # 第二次调用 requests.get() 时，会返回第二个模拟响应 mock_replies_resp
        mock_get.side_effect = [mock_mentions_resp, mock_replies_resp]
        result = self.api.get_unreplied_mentions()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], '2')

    # 实际请求测试：发推文
    def test_post_tweet_real(self):
        result = asyncio.run(self.api.post_tweet('debug'))
        # result = self.api.post_tweet('5.7')
        print(result)

    def test_post_tweet_task(self):
        from celery_queue.tasks import periodic_post_tweet
        periodic_post_tweet()

    # 实际请求测试：回复推文
    def test_reply_tweet_real(self):
        # 先发一条推文
        # tweet = self.api.post_tweet('integration test for reply')
        # tweet_id = tweet['data']['id']
        reply_result = self.api.reply_tweet('integration reply', '1917474117592441010')
        self.assertIn('data', reply_result)
        self.assertIn('id', reply_result['data'])
        self.assertEqual(reply_result['data']['text'], 'integration reply')

    # 实际请求测试：获取未回复的提及
    def test_get_unreplied_mentions_real(self):
        result = self.api.get_unreplied_mentions()
        self.assertIsInstance(result, list)

    def test_save_tokens_to_redis(self):
        """首次将 access_token、refresh_token、expires_at 信息以 tweet_token: 前缀保存到 redis 的指定位置，并验证写入"""
        redis_url = ""
        redis_client = redis.StrictRedis.from_url(redis_url)
        access_token = ""
        refresh_token = ""
        expires_at = int(time.time()) + 7200
        redis_client.set("tweet_token:twitter_access_token", access_token)
        redis_client.set("tweet_token:twitter_refresh_token", refresh_token)
        redis_client.set("tweet_token:twitter_expires_at", expires_at)
        # 验证写入
        self.assertEqual(redis_client.get("tweet_token:twitter_access_token").decode(), access_token)
        self.assertEqual(redis_client.get("tweet_token:twitter_refresh_token").decode(), refresh_token)
        self.assertEqual(int(redis_client.get("tweet_token:twitter_expires_at")), expires_at)


    def test_generate_oauth2_authorize_url_and_access_token(self):
        """串联测试：自动获取授权码并用其获取access token"""
        redirect_uri = self.api.conf.REDIRECT_URI if hasattr(self.api.conf,
                                                           'REDIRECT_URI') else "http://127.0.0.1:8000/ai/puti/chat/callback"
        scope = self.api.conf.SCOPE if hasattr(self.api.conf,
                                             'SCOPE') else "tweet.read tweet.write users.read offline.access"
        state = "teststate"
        code_challenge = "testchallenge"
        code_challenge_method = "plain"
        url = self.api.conf.generate_oauth2_authorize_url(
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )
        # self.assertIn("https://twitter.com/i/oauth2/authorize", url)
        # self.assertIn(f"client_id={config.CLIENT_ID}", url)
        # self.assertIn(f"redirect_uri={redirect_uri}", url)
        # self.assertIn(f"scope={scope.replace(' ', '+')}", url)
        # self.assertIn(f"state={state}", url)
        # self.assertIn(f"code_challenge={code_challenge}", url)
        # self.assertIn(f"code_challenge_method={code_challenge_method}", url)

        # 自动化模拟回调（实际项目中可用mock或集成测试环境自动获取code）
        # 这里假设我们能从日志或mock接口拿到code
        # 示例：code = "xxxx"，实际应自动获取
        code = "模拟获取到的code"
        code_verifier = code_challenge  # plain模式下两者一致

        # 调用token获取逻辑
        self._do_access_token_exchange(code, code_verifier, redirect_uri, self.api.conf)

    def test_refresh_access_token(self):
        """测试使用refresh token获取新的access token"""
        # 此处应该从存储中获取之前保存的refresh token
        refresh_token = "WmhzRGRqdUdPVmlPQmhaanFMQTE0X1hVRF9QZVJocDlUZHhYdmthRVhldXUwOjE3NDY1MDEwNDk3NzE6MToxOnJ0OjE"  # 替换为实际保存的refresh token

        self._do_refresh_token_exchange(refresh_token)

    def _do_refresh_token_exchange(self, refresh_token):
        import requests
        CLIENT_ID = self.api.conf.CLIENT_ID
        CLIENT_SECRET = self.api.conf.CLIENT_SECRET
        token_url = "https://api.twitter.com/2/oauth2/token"

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        auth = (CLIENT_ID, CLIENT_SECRET)

        try:
            response = requests.post(token_url, data=payload, headers=headers, auth=auth)
            response.raise_for_status()
            token_data = response.json()

            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")  # Twitter usually provides a new refresh token
            scope = token_data.get("scope")
            expires_in = token_data.get("expires_in")

            # 在实际应用中，应将新的token保存到数据库或缓存
            print("Successfully refreshed tokens:")
            print(f"  New Access Token: {new_access_token}")
            if new_refresh_token:
                print(f"  New Refresh Token: {new_refresh_token}")
            print(f"  Scope: {scope}")
            print(f"  Expires In (seconds): {expires_in}")

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_in": expires_in,
                "scope": scope
            }
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing token: {e}")
            if e.response is not None:
                print(f"Response Status Code: {e.response.status_code}")
                try:
                    print(f"Response Body: {e.response.json()}")
                except ValueError:
                    print(f"Response Body: {e.response.text}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during token refresh: {e}")
            return None

    def _do_access_token_exchange(self, authorization_code, code_verifier, redirect_uri, config):
        CLIENT_ID = config.CLIENT_ID
        CLIENT_SECRET = config.CLIENT_SECRET
        token_url = "https://api.twitter.com/2/oauth2/token"
        payload = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": CLIENT_ID,
            "code_verifier": code_verifier
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        auth = (CLIENT_ID, CLIENT_SECRET)
        try:
            response = requests.post(token_url, data=payload, headers=headers, auth=auth)
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            scope = token_data.get("scope")
            expires_in = token_data.get("expires_in")

            # 保存token到文件（在实际应用中应使用更安全的存储方式）
            token_file = str(root_dir() / 'data' / "twitter_tokens.json")
            token_store = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": int(time.time()) + expires_in,
                "scope": scope
            }

            with open(token_file, "w") as f:
                json.dump(token_store, f)

            print("Successfully obtained tokens:")
            print(f"  Access Token: {access_token}")
            if refresh_token:
                print(f"  Refresh Token: {refresh_token}")
            print(f"  Scope: {scope}")
            print(f"  Expires In (seconds): {expires_in}")
            print(f"  Tokens saved to {token_file}")

            return token_store
        except requests.exceptions.RequestException as e:
            print(f"Error exchanging code for token: {e}")
            if e.response is not None:
                print(f"Response Status Code: {e.response.status_code}")
                try:
                    print(f"Response Body: {e.response.json()}")
                except ValueError:
                    print(f"Response Body: {e.response.text}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    def get_valid_access_token(self):
        """获取有效的access token，如果过期则自动刷新"""

        token_file = str(root_dir() / 'data' / "twitter_tokens.json")

        # 检查token文件是否存在
        if not os.path.exists(token_file):
            print("No token file found. Please authorize first.")
            return None

        # 读取保存的token
        with open(token_file, "r") as f:
            token_data = json.load(f)

        current_time = int(time.time())
        expires_at = token_data.get("expires_at", 0)

        # 检查token是否过期（提前5分钟刷新）
        if current_time >= (expires_at - 300):
            print("Access token expired or will expire soon. Refreshing...")
            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                print("No refresh token available. Need to reauthorize.")
                return None

            # 使用refresh token获取新token
            new_tokens = self._do_refresh_token_exchange(refresh_token)
            if new_tokens:
                # 更新token文件
                token_data = {
                    "access_token": new_tokens["access_token"],
                    "refresh_token": new_tokens.get("refresh_token", refresh_token),
                    "expires_at": int(time.time()) + new_tokens["expires_in"],
                    "scope": new_tokens["scope"]
                }

                with open(token_file, "w") as f:
                    json.dump(token_data, f)

                print("Token refreshed and saved successfully.")
                return token_data["access_token"]
            else:
                print("Failed to refresh token.")
                return None
        else:
            print("Using existing valid access token.")
            return token_data["access_token"]

    def test_use_twitter_api_with_auto_refresh(self):
        """测试使用自动刷新token的API调用"""
        # 获取有效的access token（如果需要会自动刷新）
        access_token = self.get_valid_access_token()
        if not access_token:
            print("Failed to obtain a valid access token")
            return

        # 使用token调用Twitter API
        api_url = "https://api.twitter.com/2/users/me"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            user_data = response.json()
            print("API call successful:")
            print(f"User data: {user_data}")
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
            if e.response is not None:
                print(f"Response Status Code: {e.response.status_code}")
                try:
                    print(f"Response Body: {e.response.json()}")
                except ValueError:
                    print(f"Response Body: {e.response.text}")

    def test_get_my_id(self):
        user_id = self.api.get_my_id()
        print(f"当前用户ID: {user_id}")
        assert isinstance(user_id, str) and len(user_id) > 0, "获取的用户ID应为非空字符串"


if __name__ == '__main__':
    unittest.main()
