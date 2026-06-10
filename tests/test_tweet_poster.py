"""tweet_poster モジュールのテスト

テスト方針:
- post_tweet() のバリデーション部分は環境変数も外部APIも不要なので
  ピュアにテストできる。parametrize で複数パターンを一度に検証
"""
import pytest

import tweet_poster


@pytest.mark.parametrize(
    "invalid_text,expected_message",
    [
        ("", "空"),             # 空文字
        ("   ", "空"),          # 空白のみ(strip後に空)
        ("\n\t ", "空"),        # 改行・タブのみ
        ("a" * 281, "280文字"),  # 280字超 (境界値+1)
        ("あ" * 281, "280文字"),  # 全角でも文字数カウント (len() 基準)
    ],
    ids=["空文字", "空白のみ", "改行タブ", "281字英字", "281字全角"],
)
def test_post_tweet_不正入力はPostErrorを投げる(invalid_text, expected_message):
    """post_tweet のバリデーションが不正入力を弾くこと

    なぜこのテスト:
      X APIに無駄なリクエストを投げる前にクライアント側で
      弾くバリデーションを担保する。API側で弾かれても動くが、
      無駄なレートリミット消費を防ぐ & ユーザーに早くエラーを返す

    なぜparametrize:
      「空文字」「空白のみ」「280字超」は同じテスト構造で
      複数パターン確認したいだけなので parametrize で DRY にする。
      ids を付けておくと pytest -v で読みやすい (面接でのアピール)
    """
    with pytest.raises(tweet_poster.PostError, match=expected_message):
        tweet_poster.post_tweet(invalid_text)


def test_post_tweet_境界値280字はPostErrorを投げない_環境変数未設定で別エラー(monkeypatch):
    """280字ちょうどは長さバリデーションを通過すること (境界値テスト)

    なぜこのテスト:
      「280字超」でエラーなら「280字ちょうど」は通らないといけない。
      境界値(boundary value)は最もバグが出やすい部分なので必ず押さえる。

    補足:
      長さチェックはパスするが、その直後 _get_auth() で環境変数を
      要求するので PostError (別メッセージ) が出る。
      「長さチェックの後に認証チェックが走る」という順序も担保できる。

      monkeypatch.delenv で環境変数を明示的に消しておくのは、
      ローカルで export 済み / .env が読み込まれている環境でも
      テストが壊れないようにするため (テストの決定性を保つ)
    """
    # テスト実行環境に依存しないよう、認証系の環境変数を確実に消す
    for var in ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]:
        monkeypatch.delenv(var, raising=False)

    text = "a" * 280  # 境界値ちょうど

    with pytest.raises(tweet_poster.PostError) as exc_info:
        tweet_poster.post_tweet(text)

    # 長さエラーではなく、認証(環境変数)エラーで落ちること
    assert "280文字" not in str(exc_info.value)
    assert ".env" in str(exc_info.value) or "X_API_KEY" in str(exc_info.value)
