"""
@Author: obstacles
@Time:  2025-04-15 17:37
@Description:  
"""


def test_twitter_api():
    import requests
    import time

    # 替换成你自己的 Bearer Token
    BEARER_TOKEN = ""

    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }

    def get_user_id(username):
        url = f"https://api.twitter.com/2/users/search"
        resp = requests.get(url, headers=headers, params={'query': 'CZ 🔶 BNB'})
        resp.raise_for_status()
        return resp.json()['data']['id']

    def get_user_replies(user_id, max_pages=10):
        url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = {
            "max_results": 100,
            "tweet.fields": "in_reply_to_user_id,referenced_tweets",
        }

        all_replies = []
        next_token = None

        for _ in range(max_pages):  # 控制请求页数
            if next_token:
                params["pagination_token"] = next_token

            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            for tweet in data.get("data", []):
                refs = tweet.get("referenced_tweets", [])
                for ref in refs:
                    if ref["type"] == "replied_to":
                        all_replies.append({
                            "reply_id": tweet["id"],
                            "reply_text": tweet["text"],
                            "replied_to_id": ref["id"]
                        })

            next_token = data.get("meta", {}).get("next_token")
            if not next_token:
                break
            time.sleep(1)

        return all_replies

    def get_tweet_by_id(tweet_id):
        url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        params = {
            "tweet.fields": "author_id,text"
        }
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("text", "")
        else:
            return ""

    def build_qa_pairs(username):
        user_id = get_user_id(username)
        print(f"User ID of {username}: {user_id}")
        replies = get_user_replies(user_id)

        qa_pairs = []
        for item in replies:
            replied_text = get_tweet_by_id(item["replied_to_id"])
            if replied_text:
                qa_pairs.append({
                    "q": replied_text,
                    "a": item["reply_text"]
                })
            time.sleep(0.5)  # 防止过快请求

        return qa_pairs

    qa_data = build_qa_pairs("@cz_binance")
    print(f"共获取到 {len(qa_data)} 条问答对")
    for qa in qa_data[:5]:
        print("\nQ:", qa["q"])
        print("A:", qa["a"])
