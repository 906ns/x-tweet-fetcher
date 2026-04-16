"""Claude API によるツイート分析・文案生成モジュール"""
import os
import anthropic


class AIError(Exception):
    pass


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIError("ANTHROPIC_API_KEY が .env に設定されていません")
    return anthropic.Anthropic(api_key=api_key)


def analyze_tweets(tweets: list[dict]) -> str:
    """取得したツイートをClaudeで分析"""
    client = _get_client()

    # ツイートデータを整形（最大50件）
    tweet_text = ""
    for i, t in enumerate(tweets[:50], 1):
        tweet_text += (
            f"[{i}] {t.get('アカウント名', '')} ({t.get('日時', '')})\n"
            f"  内容: {t.get('投稿内容', '')}\n"
            f"  いいね: {t.get('いいね数', 0)} / RT: {t.get('RT数', 0)} / "
            f"インプレッション: {t.get('インプレッション数', 0)}\n\n"
        )

    prompt = f"""以下のX(旧Twitter)のツイートデータを分析してください。

## 分析してほしい項目:
1. **全体の傾向**: どんな話題が多いか、投稿のトーンや特徴
2. **エンゲージメント分析**: いいね・RT・インプレッションが高い投稿の特徴
3. **バズる投稿の法則**: 人気投稿に共通する要素
4. **投稿の改善提案**: より反応を得るためのアドバイス
5. **ハッシュタグ・キーワード**: よく使われている言葉やタグ

## ツイートデータ ({len(tweets)}件中{min(len(tweets), 50)}件を分析):
{tweet_text}

日本語で分かりやすく、箇条書きを活用して分析結果を出力してください。"""

    try:
        result_text = ""
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                result_text += text
        return result_text
    except anthropic.AuthenticationError:
        raise AIError("ANTHROPIC_API_KEY が無効です。正しいAPIキーを設定してください。")
    except anthropic.APIStatusError as e:
        raise AIError(f"Claude API エラー ({e.status_code}): {e.message}")
    except Exception as e:
        raise AIError(f"予期せぬエラー: {e}")


def generate_tweet(tweets: list[dict], topic: str = "") -> str:
    """分析結果を元にツイート文案を生成"""
    client = _get_client()

    # 人気ツイートTOP5を抽出
    sorted_tweets = sorted(tweets, key=lambda t: t.get("いいね数", 0), reverse=True)
    top_tweets = ""
    for i, t in enumerate(sorted_tweets[:5], 1):
        top_tweets += (
            f"[{i}] いいね{t.get('いいね数', 0)} / RT{t.get('RT数', 0)}\n"
            f"  {t.get('投稿内容', '')}\n\n"
        )

    topic_instruction = f"テーマ: {topic}" if topic else "特にテーマ指定なし（人気ツイートの傾向に合わせて）"

    prompt = f"""以下の人気ツイートの文体・傾向を参考にして、バズりそうなツイート案を3つ生成してください。

## 参考にする人気ツイート:
{top_tweets}

## 指示:
- {topic_instruction}
- 140文字以内
- 参考ツイートの文体やトーンを真似る
- 各案の後に「(狙い: ○○)」と簡単な戦略説明をつける
- ハッシュタグがあれば適宜含める

## 出力フォーマット:
【案1】ツイート本文
(狙い: ○○)

【案2】ツイート本文
(狙い: ○○)

【案3】ツイート本文
(狙い: ○○)
"""

    try:
        result_text = ""
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=2048,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                result_text += text
        return result_text
    except anthropic.AuthenticationError:
        raise AIError("ANTHROPIC_API_KEY が無効です。正しいAPIキーを設定してください。")
    except anthropic.APIStatusError as e:
        raise AIError(f"Claude API エラー ({e.status_code}): {e.message}")
    except Exception as e:
        raise AIError(f"予期せぬエラー: {e}")
