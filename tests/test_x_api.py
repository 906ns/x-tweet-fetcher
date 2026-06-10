"""x_api モジュールのテスト

テスト方針:
- `_normalize_tweets` は純関数なのでモック不要でそのままテスト
- `_request` は外部HTTPを叩くのでモック化して429エラーハンドリングを確認
"""
from unittest.mock import patch, MagicMock

import pytest

import x_api


# ========== _normalize_tweets のテスト ==========


def test_normalize_tweets_正常系():
    """API応答をCSV向けの辞書リストに整形できること

    なぜこのテスト:
      このアプリのコア処理。X APIの生レスポンスから
      CSV出力用のフィールドへマッピングする動作が壊れると
      全機能が使い物にならなくなるので最優先でテストする
    """
    api_response = {
        "data": [
            {
                "id": "1",
                "text": "こんにちは\nテストツイート",  # 改行が半角スペースに置換されるか
                "created_at": "2026-04-23T10:00:00Z",
                "author_id": "user_a",
                "public_metrics": {
                    "like_count": 100,
                    "retweet_count": 20,
                    "impression_count": 5000,
                },
            }
        ],
        "includes": {
            "users": [
                {"id": "user_a", "username": "mia_dev", "name": "みあ"},
            ]
        },
    }

    rows = x_api._normalize_tweets(api_response)

    assert len(rows) == 1
    row = rows[0]
    assert row["投稿内容"] == "こんにちは テストツイート"  # \n → 半角スペース
    assert row["日時"] == "2026-04-23T10:00:00Z"
    assert row["いいね数"] == 100
    assert row["RT数"] == 20
    assert row["インプレッション数"] == 5000
    assert row["アカウント名"] == "@mia_dev"  # username には @ が付く


def test_normalize_tweets_data無し空リスト():
    """APIレスポンスに "data" が無いとき空リストを返すこと

    なぜこのテスト:
      X APIは検索結果0件のとき data キーを返さないことがある
      (空配列ではなくキーそのものが無い)。この分岐を落とすと
      TypeErrorで500エラーになる。エッジケース確認
    """
    api_response = {"meta": {"result_count": 0}}  # data キー無し

    rows = x_api._normalize_tweets(api_response)

    assert rows == []


def test_normalize_tweets_author情報欠損():
    """users_map に author_id が無いとき、アカウント名が空文字になること

    なぜこのテスト:
      API側のexpansionsが欠ける/期待しないレスポンスが返ってきた際、
      KeyError で落ちずに「空文字で進める」フォールバック動作を担保。
      実運用では「鍵アカウント化でuser情報が取れない」等で起きうる
    """
    api_response = {
        "data": [
            {
                "id": "1",
                "text": "author情報が無いツイート",
                "created_at": "2026-04-23T10:00:00Z",
                "author_id": "unknown_user",  # users_map に存在しない
                "public_metrics": {"like_count": 5, "retweet_count": 1, "impression_count": 50},
            }
        ],
        "includes": {"users": []},  # 空
    }

    rows = x_api._normalize_tweets(api_response)

    assert len(rows) == 1
    assert rows[0]["アカウント名"] == ""  # 落ちずに空文字


# ========== _request のテスト (モック使用) ==========


def test_request_レートリミット時にXAPIErrorを投げる(monkeypatch):
    """HTTP 429 のとき XAPIError を raise すること

    なぜこのテスト:
      X APIは無料プランの上限が厳しく、本番運用で頻繁に起きる。
      429を黙って無視すると「0件取得」として誤動作するので、
      明示的にエラー化して呼び出し側に伝える動作を保証する

    テスト技法:
      外部HTTPを叩きたくないので requests.get を MagicMock で差し替え。
      monkeypatch で環境変数 X_BEARER_TOKEN も仮設定（_headers のチェックを通すため）
    """
    monkeypatch.setenv("X_BEARER_TOKEN", "dummy_token")

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Too Many Requests"

    with patch("x_api.requests.get", return_value=mock_response):
        with pytest.raises(x_api.XAPIError, match="レートリミット"):
            x_api._request("https://api.twitter.com/2/test", {})
