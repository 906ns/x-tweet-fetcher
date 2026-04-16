"""X API v2 連携モジュール"""
import os
import requests
from typing import Optional

API_BASE = "https://api.twitter.com/2"

# 取得するツイートフィールド
TWEET_FIELDS = "created_at,public_metrics,author_id,text"
USER_FIELDS = "username,name"
EXPANSIONS = "author_id"


class XAPIError(Exception):
    pass


def _headers() -> dict:
    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        raise XAPIError("X_BEARER_TOKEN が .env に設定されていません")
    return {"Authorization": f"Bearer {token}"}


def _request(url: str, params: dict) -> dict:
    resp = requests.get(url, headers=_headers(), params=params, timeout=30)
    if resp.status_code == 429:
        raise XAPIError("レートリミットに達しました。しばらく待ってから再試行してください。")
    if resp.status_code != 200:
        raise XAPIError(f"APIエラー ({resp.status_code}): {resp.text}")
    return resp.json()


def get_user_id_by_username(username: str) -> tuple[str, str]:
    """ユーザー名からユーザーIDと表示名を取得"""
    username = username.lstrip("@")
    url = f"{API_BASE}/users/by/username/{username}"
    data = _request(url, {"user.fields": "username,name"})
    if "data" not in data:
        raise XAPIError(f"ユーザー '{username}' が見つかりません")
    return data["data"]["id"], data["data"]["name"]


def get_me() -> tuple[str, str, str]:
    """認証ユーザー(自分)の情報を取得 (id, username, name)"""
    url = f"{API_BASE}/users/me"
    data = _request(url, {"user.fields": "username,name"})
    if "data" not in data:
        raise XAPIError("自分のアカウント情報を取得できませんでした (OAuth2ユーザーコンテキストが必要な場合があります)")
    d = data["data"]
    return d["id"], d["username"], d["name"]


def fetch_user_tweets(username: str, max_results: int = 100) -> list[dict]:
    """指定ユーザーのツイートを取得"""
    user_id, _ = get_user_id_by_username(username)
    url = f"{API_BASE}/users/{user_id}/tweets"
    # X APIの max_results は 5〜100
    mr = max(5, min(100, max_results))
    params = {
        "max_results": mr,
        "tweet.fields": TWEET_FIELDS,
        "expansions": EXPANSIONS,
        "user.fields": USER_FIELDS,
        "exclude": "retweets,replies",
    }
    data = _request(url, params)
    return _normalize_tweets(data)


def fetch_home_timeline(max_results: int = 100) -> list[dict]:
    """自分のホームタイムラインを取得 (要 OAuth2 User Context)"""
    # 自分のIDを取得
    my_id, _, _ = get_me()
    url = f"{API_BASE}/users/{my_id}/timelines/reverse_chronological"
    mr = max(5, min(100, max_results))
    params = {
        "max_results": mr,
        "tweet.fields": TWEET_FIELDS,
        "expansions": EXPANSIONS,
        "user.fields": USER_FIELDS,
    }
    data = _request(url, params)
    return _normalize_tweets(data)


def _normalize_tweets(data: dict) -> list[dict]:
    """API応答をCSV出力用の辞書リストに整形"""
    if "data" not in data:
        return []

    # author_id → username, name のマップ作成
    users_map = {}
    for u in data.get("includes", {}).get("users", []):
        users_map[u["id"]] = {"username": u.get("username", ""), "name": u.get("name", "")}

    rows = []
    for t in data["data"]:
        metrics = t.get("public_metrics", {})
        user = users_map.get(t.get("author_id", ""), {})
        rows.append({
            "投稿内容": t.get("text", "").replace("\n", " "),
            "日時": t.get("created_at", ""),
            "いいね数": metrics.get("like_count", 0),
            "RT数": metrics.get("retweet_count", 0),
            "アカウント名": f"@{user.get('username', '')}" if user.get("username") else "",
            "インプレッション数": metrics.get("impression_count", 0),
        })
    return rows
