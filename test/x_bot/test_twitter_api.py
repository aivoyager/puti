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
        tweet = self.api.post_tweet('integration test for reply')
        tweet_id = tweet['data']['id']
        reply_result = self.api.reply_tweet('integration reply', tweet_id)
        self.assertIn('data', reply_result)
        self.assertIn('id', reply_result['data'])
        self.assertEqual(reply_result['data']['text'], 'integration reply')

    # 实际请求测试：获取未回复的提及
    def test_get_unreplied_mentions_real(self):
        result = self.api.get_unreplied_mentions()
        self.assertIsInstance(result, list)

    def test_generate_oauth2_authorize_url(self):
        """测试 TwitterConfig 生成 OAuth2 授权链接，参数直接从配置读取"""
        config = TwitterConfig()
        redirect_uri = config.REDIRECT_URI if hasattr(config, 'REDIRECT_URI') else "https://example.com/callback"
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
        self.assertIn("https://twitter.com/i/oauth2/authorize", url)
        self.assertIn(f"client_id={config.CLIENT_ID}", url)
        self.assertIn(f"redirect_uri={redirect_uri}", url)
        self.assertIn(f"scope={scope.replace(' ', '+')}", url)
        self.assertIn(f"state={state}", url)
        self.assertIn(f"code_challenge={code_challenge}", url)
        self.assertIn(f"code_challenge_method={code_challenge_method}", url)

if __name__ == '__main__':
    unittest.main()