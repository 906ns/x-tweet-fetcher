"""X ツイート取得・分析・投稿ツール - Flask サーバー"""
import csv
import io
import os
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify
from dotenv import load_dotenv

import x_api
import ai_analyzer
import tweet_poster

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

app = Flask(__name__)
app.secret_key = os.urandom(24)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_HEADERS = ["投稿内容", "日時", "いいね数", "RT数", "アカウント名", "インプレッション数"]

# メモリ上に最後に取得したツイートを保持（分析・生成で使う）
_last_tweets: list[dict] = []


@app.route("/")
def index():
    return render_template("index.html")


# ===== ツイート取得 =====

@app.route("/api/fetch_user", methods=["POST"])
def fetch_user():
    global _last_tweets
    username = (request.json or {}).get("username", "").strip()
    max_results = int((request.json or {}).get("max_results", 100))
    if not username:
        return jsonify({"error": "ユーザー名を入力してください"}), 400
    try:
        rows = x_api.fetch_user_tweets(username, max_results)
        _last_tweets = rows
        filename = _save_csv(rows, f"user_{username.lstrip('@')}")
        return jsonify({"count": len(rows), "filename": filename, "preview": rows[:5]})
    except x_api.XAPIError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"予期せぬエラー: {e}"}), 500


@app.route("/api/fetch_timeline", methods=["POST"])
def fetch_timeline():
    global _last_tweets
    max_results = int((request.json or {}).get("max_results", 100))
    try:
        rows = x_api.fetch_home_timeline(max_results)
        _last_tweets = rows
        filename = _save_csv(rows, "timeline")
        return jsonify({"count": len(rows), "filename": filename, "preview": rows[:5]})
    except x_api.XAPIError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"予期せぬエラー: {e}"}), 500


# ===== AI分析 =====

@app.route("/api/analyze", methods=["POST"])
def analyze():
    global _last_tweets
    if not _last_tweets:
        return jsonify({"error": "先にツイートを取得してください"}), 400
    try:
        result = ai_analyzer.analyze_tweets(_last_tweets)
        return jsonify({"analysis": result, "tweet_count": len(_last_tweets)})
    except ai_analyzer.AIError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"予期せぬエラー: {e}"}), 500


# ===== ツイート文案生成 =====

@app.route("/api/generate", methods=["POST"])
def generate():
    global _last_tweets
    if not _last_tweets:
        return jsonify({"error": "先にツイートを取得してください"}), 400
    topic = (request.json or {}).get("topic", "")
    try:
        result = ai_analyzer.generate_tweet(_last_tweets, topic)
        return jsonify({"generated": result})
    except ai_analyzer.AIError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"予期せぬエラー: {e}"}), 500


# ===== ツイート投稿 =====

@app.route("/api/post_tweet", methods=["POST"])
def post_tweet():
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "投稿するテキストを入力してください"}), 400
    try:
        result = tweet_poster.post_tweet(text)
        return jsonify(result)
    except tweet_poster.PostError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"予期せぬエラー: {e}"}), 500


# ===== CSV アップロード =====

@app.route("/api/upload_csv", methods=["POST"])
def upload_csv():
    global _last_tweets
    if "file" not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "CSVファイルを選択してください"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        reader = csv.DictReader(stream)
        rows = []
        for row in reader:
            rows.append({
                "投稿内容": row.get("投稿内容", ""),
                "日時": row.get("日時", ""),
                "いいね数": int(row.get("いいね数", 0) or 0),
                "RT数": int(row.get("RT数", 0) or 0),
                "アカウント名": row.get("アカウント名", ""),
                "インプレッション数": int(row.get("インプレッション数", 0) or 0),
            })
        if not rows:
            return jsonify({"error": "CSVにデータがありません"}), 400

        _last_tweets = rows
        return jsonify({"count": len(rows), "preview": rows[:5]})
    except Exception as e:
        return jsonify({"error": f"CSV読み込みエラー: {e}"}), 500


# ===== ダウンロード =====

@app.route("/download/<filename>")
def download(filename):
    safe = os.path.basename(filename)
    path = os.path.join(OUTPUT_DIR, safe)
    if not os.path.exists(path):
        return "ファイルが見つかりません", 404
    return send_file(path, as_attachment=True, download_name=safe)


def _save_csv(rows: list[dict], prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{ts}.csv"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return filename


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
