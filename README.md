# X ツイート取得・AI分析ツール

X API v2 でツイートを取得し、Claude APIで傾向分析・投稿文案の生成まで行うWebツール。

## 機能

- 指定ユーザーのツイートを取得（最大100件）
- 自分のホームタイムラインを取得（最大100件）
- CSV出力（投稿内容/日時/いいね数/RT数/アカウント名/インプレッション数）
- **AI分析（Claude API）**: 取得したツイートの傾向・エンゲージメント分析、バズる投稿の共通要素の抽出
- **投稿文案の生成（Claude API)**: 分析結果をもとに、指定テーマの投稿文案を生成
- ツイート投稿（X API経由）

## 技術スタック

| 領域 | 技術 |
|---|---|
| バックエンド | Python / Flask |
| 外部API | X API v2 / Claude API（Anthropic） |
| フロントエンド | Jinja2 + Vanilla JS |

## セットアップ

```bash
cd x-tweet-fetcher
pip install -r requirements.txt
cp .env.example .env
```

`.env` に以下を設定:

| 変数 | 用途 | 取得先 |
|---|---|---|
| `X_BEARER_TOKEN` | ツイート取得 | https://developer.x.com |
| `ANTHROPIC_API_KEY` | AI分析・文案生成 | https://console.anthropic.com/settings/keys |
| `CLAUDE_MODEL` | 使用モデルの指定（任意、省略時はデフォルト） | - |

## 起動

```bash
python app.py
```

ブラウザで http://127.0.0.1:5000 を開く。

## テスト

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## 注意事項

- **X API Basicプラン以上が必要**（Freeではツイート取得不可）
- タイムライン取得は **OAuth2 User Context** が必要です。Bearer Token（App-only）では `/users/me` や `timelines/reverse_chronological` エンドポイントは使えません。タイムライン機能を使う場合は OAuth2 のユーザートークンに差し替えてください
- インプレッション数は自分のツイートのみ取得可能な場合があります
- レートリミットに注意（Basic: 15分あたり一定回数）

## ファイル構成

```
x-tweet-fetcher/
├── app.py              # Flaskサーバー・ルーティング
├── x_api.py            # X API 連携（取得）
├── tweet_poster.py     # X API 連携（投稿）
├── ai_analyzer.py      # Claude APIによる分析・文案生成
├── tests/              # pytest（ユニットテスト）
├── templates/index.html
├── static/             # CSS / JS
├── output/             # CSV出力先
├── .env.example
└── requirements.txt
```
