# X ツイート取得ツール

X API v2 を使ってツイートを取得し、CSV出力するシンプルなWebツール。

## 機能

- 指定ユーザーのツイートを取得（最大100件）
- 自分のホームタイムラインを取得（最大100件）
- CSV出力（投稿内容/日時/いいね数/RT数/アカウント名/インプレッション数）

## セットアップ

```bash
cd x-tweet-fetcher
pip install -r requirements.txt
cp .env.example .env
# .env を編集して X_BEARER_TOKEN を設定
```

## 起動

```bash
python app.py
```

ブラウザで http://127.0.0.1:5000 を開く。

## 注意事項

- **X API Basicプラン以上が必要**（Freeではツイート取得不可）
- タイムライン取得は **OAuth2 User Context** が必要です。Bearer Token（App-only）では `/users/me` や `timelines/reverse_chronological` エンドポイントは使えません。タイムライン機能を使う場合は OAuth2 のユーザートークンに差し替えてください
- インプレッション数は自分のツイートのみ取得可能な場合があります
- レートリミットに注意（Basic: 15分あたり一定回数）

## ファイル構成

```
x-tweet-fetcher/
├── app.py              # Flaskサーバー
├── x_api.py            # X API 連携
├── templates/index.html
├── output/             # CSV出力先
├── .env.example
└── requirements.txt
```
