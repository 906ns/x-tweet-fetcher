"""X ツイート投稿モジュール (OAuth 1.0a)"""
import os
import json
import unicodedata 
import requests
from requests_oauthlib import OAuth1


class PostError(Exception):
    pass


# ↓ ここに新しい関数を追加
def count_tweet_length(text: str) -> int:
    """Xのカウントルール（全角2・半角1）で文字数を数える"""
    count = 0
    for char in text:
        if unicodedata.east_asian_width(char) == 'W' or unicodedata.east_asian_width(char) == 'F':
            count += 2
        else:
            count += 1
    return count

def _get_auth() -> OAuth1:
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_secret = os.getenv("X_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        missing = []
        if not api_key: missing.append("X_API_KEY")
        if not api_secret: missing.append("X_API_SECRET")
        if not access_token: missing.append("X_ACCESS_TOKEN")
        if not access_secret: missing.append("X_ACCESS_SECRET")
        raise PostError(f".env に以下のキーが未設定です: {', '.join(missing)}")

    return OAuth1(api_key, api_secret, access_token, access_secret)


def post_tweet(text: str) -> dict:
    """ツイートを投稿する"""
    if not text or not text.strip():
        raise PostError("投稿するテキストが空です")

    text = text.strip()
    if count_tweet_length(text) > 280:
        raise PostError(f"ツイートが280文字を超えています ({count_tweet_length(text)}カウント)")
    
    url = "https://api.twitter.com/2/tweets"
    auth = _get_auth()

    payload = {"text": text}
    resp = requests.post(
        url,
        auth=auth,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if resp.status_code == 429:
        raise PostError("レートリミットに達しました。しばらく待ってください。")
    if resp.status_code not in (200, 201):
        raise PostError(f"投稿エラー ({resp.status_code}): {resp.text}")

    data = resp.json()
    tweet_id = data.get("data", {}).get("id", "")
    return {
        "success": True,
        "tweet_id": tweet_id,
        "url": f"https://x.com/i/status/{tweet_id}" if tweet_id else "",
        "text": text,
    }
