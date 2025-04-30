import unittest
from unittest.mock import patch, MagicMock
from client.twitter.x_api import TwitterAPI
from conf.client_config import TwitterConfig


class TestTwitterAPI(unittest.TestCase):
    def setUp(self):
        """为每个测试方法准备相同的初始环境，避免重复代码"""
        self.config = TwitterConfig()
        self.api = TwitterAPI(self.config)

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
        result = self.api.post_tweet('integration test tweet')
        self.assertIn('data', result)
        self.assertIn('id', result['data'])
        self.assertEqual(result['data']['text'], 'integration test tweet')

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

    def test_generate_oauth2_authorize_url_and_access_token(self):
        """串联测试：自动获取授权码并用其获取access token"""
        config = TwitterConfig()
        redirect_uri = config.REDIRECT_URI if hasattr(config, 'REDIRECT_URI') else "http://127.0.0.1:8000/ai/puti/chat/callback"
        scope = config.SCOPE if hasattr(config, 'SCOPE') else "tweet.read tweet.write users.read offline.access"
        state = "teststate"
        code_challenge = "testchallenge"
        code_challenge_method = "plain"
        url = config.generate_oauth2_authorize_url(
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
        self._do_access_token_exchange(code, code_verifier, redirect_uri, config)

    def _do_access_token_exchange(self, authorization_code, code_verifier, redirect_uri, config):
        import requests
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
            print("Successfully obtained tokens:")
            print(f"  Access Token: {access_token}")
            if refresh_token:
                print(f"  Refresh Token: {refresh_token}")
            print(f"  Scope: {scope}")
            print(f"  Expires In (seconds): {expires_in}")
        except requests.exceptions.RequestException as e:
            print(f"Error exchanging code for token: {e}")
            if e.response is not None:
                print(f"Response Status Code: {e.response.status_code}")
                try:
                    print(f"Response Body: {e.response.json()}")
                except ValueError:
                    print(f"Response Body: {e.response.text}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    unittest.main()