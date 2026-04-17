/* ===========================
   X Tweet Fetcher - Main JS
   =========================== */

let fetchedCount = 0;

// AbortController for cancellable requests
let fetchController = null;
let analyzeController = null;
let generateController = null;

// --- Utility ---

async function postJSON(url, body = {}, signal = null) {
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
  if (signal) options.signal = signal;
  const res = await fetch(url, options);
  return { ok: res.ok, data: await res.json() };
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function setLoading(btnId, loading, defaultText) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  btn.innerHTML = loading
    ? `<span class="spinner"></span> ${defaultText}中...`
    : defaultText;
}

function showLoading(elId, message) {
  document.getElementById(elId).innerHTML = `
    <div class="loading-msg">
      <div class="spinner"></div>
      <span>${message}</span>
    </div>`;
}

function enableStep2(count) {
  fetchedCount = count;
  document.getElementById('btn-analyze').disabled = false;
  document.getElementById('btn-generate').disabled = false;
  const badge = document.getElementById('tweet-count-badge');
  badge.textContent = `${count}件取得済み`;
  badge.style.display = 'inline-flex';
}

// --- Step 1: Fetch ---

function renderFetchResult(elId, result) {
  const el = document.getElementById(elId);
  if (!result.ok) {
    el.innerHTML = `<div class="result-error">❌ ${escapeHtml(result.data.error)}</div>`;
    return;
  }
  const d = result.data;
  enableStep2(d.count);

  let html = `<div class="result-success">✅ ${d.count} 件読み込みました。`;
  if (d.filename) {
    html += `<a class="download-link" href="/download/${d.filename}" download>📥 CSVをダウンロード</a>`;
  }
  html += `</div>`;

  if (d.preview && d.preview.length) {
    html += `<div class="preview-wrap"><div class="preview-label">プレビュー（先頭5件）</div>`;
    d.preview.forEach(p => {
      html += `
        <div class="preview-item">
          <div class="preview-meta">
            <strong>${escapeHtml(p['アカウント名'])}</strong>
            <span>♥ ${Number(p['いいね数']).toLocaleString()}</span>
            <span>🔁 ${Number(p['RT数']).toLocaleString()}</span>
            <span>👁 ${Number(p['インプレッション数']).toLocaleString()}</span>
          </div>
          <div class="preview-text">${escapeHtml(String(p['投稿内容']).slice(0, 120))}${String(p['投稿内容']).length > 120 ? '…' : ''}</div>
        </div>`;
    });
    html += `</div>`;
  }

  el.innerHTML = html;
}

function showFetchCancel(show) {
  document.getElementById('btn-user').style.display = show ? 'none' : 'inline-flex';
  document.getElementById('btn-tl').style.display = show ? 'none' : 'inline-flex';
  document.getElementById('btn-cancel-fetch').style.display = show ? 'inline-flex' : 'none';
}

function cancelFetch() {
  if (fetchController) fetchController.abort();
}

async function fetchUser() {
  const username = document.getElementById('username').value.trim();
  const max_results = parseInt(document.getElementById('user_count').value);
  const el = document.getElementById('result-fetch');

  if (!username) {
    el.innerHTML = `<div class="result-error">ユーザー名を入力してください</div>`;
    return;
  }

  fetchController = new AbortController();
  showFetchCancel(true);
  showLoading('result-fetch', 'ツイートを取得しています...');

  try {
    const r = await postJSON('/api/fetch_user', { username, max_results }, fetchController.signal);
    renderFetchResult('result-fetch', r);
  } catch (e) {
    if (e.name === 'AbortError') {
      el.innerHTML = `<div class="result-error">⏹ 取得をキャンセルしました</div>`;
    } else {
      el.innerHTML = `<div class="result-error">❌ ${escapeHtml(e.message)}</div>`;
    }
  } finally {
    fetchController = null;
    showFetchCancel(false);
  }
}

async function fetchTimeline() {
  const max_results = parseInt(document.getElementById('user_count').value);

  fetchController = new AbortController();
  showFetchCancel(true);
  showLoading('result-fetch', 'タイムラインを取得しています...');

  try {
    const r = await postJSON('/api/fetch_timeline', { max_results }, fetchController.signal);
    renderFetchResult('result-fetch', r);
  } catch (e) {
    if (e.name === 'AbortError') {
      document.getElementById('result-fetch').innerHTML =
        `<div class="result-error">⏹ 取得をキャンセルしました</div>`;
    } else {
      document.getElementById('result-fetch').innerHTML =
        `<div class="result-error">❌ ${escapeHtml(e.message)}</div>`;
    }
  } finally {
    fetchController = null;
    showFetchCancel(false);
  }
}

// --- CSV Upload ---

async function uploadCSV() {
  const input = document.getElementById('csv-file');
  const el = document.getElementById('result-fetch');

  if (!input.files || !input.files[0]) {
    el.innerHTML = `<div class="result-error">CSVファイルを選択してください</div>`;
    return;
  }

  const formData = new FormData();
  formData.append('file', input.files[0]);

  setLoading('btn-upload-csv', true, 'CSVを読み込む');
  showLoading('result-fetch', 'CSVを読み込んでいます...');

  try {
    const res = await fetch('/api/upload_csv', { method: 'POST', body: formData });
    const data = await res.json();
    renderFetchResult('result-fetch', { ok: res.ok, data });
  } catch (e) {
    el.innerHTML = `<div class="result-error">❌ 読み込みエラー: ${escapeHtml(e.message)}</div>`;
  }

  setLoading('btn-upload-csv', false, 'CSVを読み込む');
  input.value = '';
}

// --- Step 2: Analyze ---

async function analyzeTweets() {
  // キャンセル中なら無視
  if (analyzeController) return;

  analyzeController = new AbortController();
  const { signal } = analyzeController;

  document.getElementById('btn-analyze').style.display = 'none';
  document.getElementById('btn-cancel-analyze').style.display = 'inline-flex';
  showLoading('result-analyze', 'Claude が分析中です。少々お待ちください...');

  try {
    const r = await postJSON('/api/analyze', {}, signal);
    if (!r.ok) {
      document.getElementById('result-analyze').innerHTML =
        `<div class="result-error">❌ ${escapeHtml(r.data.error)}</div>`;
    } else {
      document.getElementById('result-analyze').innerHTML =
        `<div class="analysis-box">${escapeHtml(r.data.analysis)}</div>`;
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      document.getElementById('result-analyze').innerHTML =
        `<div class="result-error">⏹ 分析をキャンセルしました</div>`;
    } else {
      document.getElementById('result-analyze').innerHTML =
        `<div class="result-error">❌ ${escapeHtml(e.message)}</div>`;
    }
  } finally {
    analyzeController = null;
    document.getElementById('btn-analyze').style.display = 'inline-flex';
    document.getElementById('btn-cancel-analyze').style.display = 'none';
  }
}

function cancelAnalyze() {
  if (analyzeController) {
    analyzeController.abort();
  }
}

// --- Step 3: Generate & Post ---

async function generateTweet() {
  if (generateController) return;

  generateController = new AbortController();
  const { signal } = generateController;
  const topic = document.getElementById('topic').value.trim();

  document.getElementById('btn-generate').style.display = 'none';
  document.getElementById('btn-cancel-generate').style.display = 'inline-flex';
  showLoading('result-generate', 'Claude がツイート案を生成中...');

  try {
    const r = await postJSON('/api/generate', { topic }, signal);
    if (!r.ok) {
      document.getElementById('result-generate').innerHTML =
        `<div class="result-error">❌ ${escapeHtml(r.data.error)}</div>`;
    } else {
      document.getElementById('result-generate').innerHTML =
        `<div class="generated-box">${escapeHtml(r.data.generated)}</div>`;
      document.getElementById('post-area').style.display = 'block';
      document.getElementById('post-area').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      document.getElementById('result-generate').innerHTML =
        `<div class="result-error">⏹ 生成をキャンセルしました</div>`;
    } else {
      document.getElementById('result-generate').innerHTML =
        `<div class="result-error">❌ ${escapeHtml(e.message)}</div>`;
    }
  } finally {
    generateController = null;
    document.getElementById('btn-generate').style.display = 'inline-flex';
    document.getElementById('btn-cancel-generate').style.display = 'none';
  }
}

function cancelGenerate() {
  if (generateController) {
    generateController.abort();
  }
}

function updateCharCount() {
  const text = document.getElementById('tweet-text').value;
  const el = document.getElementById('char-count');
  el.textContent = `${text.length} / 280文字`;
  el.className = text.length > 280 ? 'char-count over' : 'char-count';
}

async function postTweet() {
  const text = document.getElementById('tweet-text').value.trim();
  const el = document.getElementById('result-post');

  if (!text) {
    el.innerHTML = `<div class="result-error">テキストを入力してください</div>`;
    return;
  }

  if (!confirm(`このツイートを投稿しますか？\n\n${text}`)) return;

  setLoading('btn-post', true, '投稿する');

  const r = await postJSON('/api/post_tweet', { text });

  if (!r.ok) {
    el.innerHTML = `<div class="result-error">❌ ${escapeHtml(r.data.error)}</div>`;
  } else {
    el.innerHTML = `
      <div class="result-success">
        ✅ 投稿しました！
        <a href="${r.data.url}" target="_blank" class="download-link">ツイートを見る →</a>
      </div>`;
  }

  setLoading('btn-post', false, '投稿する');
}
