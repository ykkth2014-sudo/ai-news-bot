#!/usr/bin/env python3
"""
AI ニュースまとめ自動生成スクリプト
毎朝 Claude API を使って国内・世界のAIニュースをHTMLレポートにまとめ、
GitHub Pages で公開しメールでリンクを送信する
"""

import anthropic
import smtplib
import os
import subprocess
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── 設定 ──────────────────────────────────────────────
JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST).strftime("%Y年%m月%d日")
TODAY_FILE = datetime.now(JST).strftime("%Y-%m-%d")

ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
MAIL_TO            = os.environ["MAIL_TO"]
GITHUB_REPOSITORY  = os.environ.get("GITHUB_REPOSITORY", "")
# ─────────────────────────────────────────────────────


PROMPT_DOMESTIC = f"""
あなたは優秀なAIニュースキュレーターです。
今日（{TODAY}）の日本国内の最新AIニュースを調査し、
以下の4カテゴリで合計10件以上のニュースをJSON形式で出力してください。

カテゴリ：
1. モデル技術（新しいAIモデル、論文、技術ブレークスルー）
2. ビジネス（企業動向、資金調達、新サービス）
3. 規制政策（AI規制、政府の動き、法制度）
4. 製品ツール（新しいAIツール、アプリのリリース）

出力形式（JSONのみ、説明文不要）：
{{
  "categories": [
    {{
      "name": "モデル技術",
      "summary": "このカテゴリの1〜2行の概要",
      "items": [
        {{
          "title": "ニュースタイトル",
          "body": "ニュース詳細（3〜5文）",
          "url": "情報源URL",
          "importance": "高"
        }}
      ]
    }}
  ]
}}

importanceは「高」「中」「低」のいずれか。
各カテゴリ最低2件以上。合計10件以上必須。
"""

PROMPT_WORLD = f"""
あなたは優秀なAIニュースキュレーターです。
今日（{TODAY}）の世界（主に米国・欧州・中国など）の最新AIニュースを調査し、
以下の4カテゴリで合計10件以上のニュースをJSON形式で出力してください。
日本のニュースは除外し、海外のニュースのみを対象としてください。

カテゴリ：
1. モデル技術（新しいAIモデル、論文、技術ブレークスルー）
2. ビジネス（企業動向、資金調達、新サービス）
3. 規制政策（AI規制、政府の動き、法制度）
4. 製品ツール（新しいAIツール、アプリのリリース）

出力形式（JSONのみ、説明文不要）：
{{
  "categories": [
    {{
      "name": "モデル技術",
      "summary": "このカテゴリの1〜2行の概要",
      "items": [
        {{
          "title": "ニュースタイトル（日本語）",
          "body": "ニュース詳細（3〜5文、日本語）",
          "url": "情報源URL",
          "importance": "高"
        }}
      ]
    }}
  ]
}}

importanceは「高」「中」「低」のいずれか。
各カテゴリ最低2件以上。合計10件以上必須。
"""


def fetch_news(prompt: str) -> dict:
    """Claude API を呼んでニュースをJSON取得"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )
    text = ""
    for block in message.content:
        if block.type == "text":
            text += block.text

    # JSON部分を抽出
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    import json
    return json.loads(text)


def importance_badge(imp: str) -> str:
    cls = {"高": "high", "中": "medium", "低": "low"}.get(imp, "low")
    return f'<span class="badge {cls}">{imp}</span>'


def render_section(data: dict, color: str) -> str:
    """カテゴリデータからHTMLセクションを生成"""
    html = '<div class="summary-grid">'
    for cat in data["categories"]:
        html += f"""
        <div class="summary-card">
          <strong>{cat['name']}</strong>
          <p>{cat['summary']}</p>
        </div>"""
    html += "</div>"

    for cat in data["categories"]:
        html += f"""
        <div class="category-section">
          <div class="category-title" style="color:{color}">📁 {cat['name']}</div>"""
        for item in cat["items"]:
            badge = importance_badge(item.get("importance", "中"))
            html += f"""
          <details>
            <summary>{item['title']} {badge}</summary>
            <div class="detail-content">
              <p>{item['body']}</p>
              <p style="margin-top:10px"><a href="{item['url']}" target="_blank">🔗 情報源を見る</a></p>
            </div>
          </details>"""
        html += "</div>"
    return html


def build_html(domestic: dict, world: dict) -> str:
    dom_html = render_section(domestic, "#e74c3c")
    wld_html = render_section(world, "#2980b9")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI ニュースまとめ - {TODAY}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; background: #f0f2f5; }}
    header {{ background: linear-gradient(135deg, #1a1a2e, #0f3460); color: white; padding: 36px 32px; border-radius: 16px; margin-bottom: 28px; }}
    h1 {{ font-size: 1.9em; }} .date {{ opacity: 0.75; margin-top: 6px; }}
    .tab-container {{ display: flex; margin-bottom: 24px; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
    .tab-btn {{ flex: 1; padding: 16px; border: none; cursor: pointer; font-size: 1.05em; font-weight: 700; background: white; color: #888; transition: all 0.2s; }}
    .tab-btn.active.domestic {{ background: #e74c3c; color: white; }}
    .tab-btn.active.world {{ background: #2980b9; color: white; }}
    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(2,1fr); gap: 14px; margin-bottom: 24px; }}
    .summary-card {{ background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); border-left: 4px solid #e74c3c; }}
    #tab-world .summary-card {{ border-left-color: #2980b9; }}
    .summary-card strong {{ display: block; margin-bottom: 5px; }}
    .summary-card p {{ font-size: 0.88em; color: #555; line-height: 1.5; }}
    .category-section {{ background: white; border-radius: 14px; padding: 22px; margin-bottom: 18px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
    .category-title {{ font-size: 1.2em; font-weight: 700; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 2px solid #f0f2f5; }}
    details {{ border: 1px solid #e8e8e8; border-radius: 10px; margin-bottom: 8px; overflow: hidden; }}
    summary {{ padding: 13px 16px; cursor: pointer; font-weight: 600; font-size: 0.92em; list-style: none; display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
    summary::-webkit-details-marker {{ display: none; }}
    summary:hover {{ background: #fafafa; }}
    summary::after {{ content: "▼"; font-size: 0.7em; color: #aaa; }}
    details[open] summary::after {{ content: "▲"; }}
    .detail-content {{ padding: 16px 18px; border-top: 1px solid #f0f0f0; color: #444; line-height: 1.75; font-size: 0.9em; }}
    .badge {{ font-size: 0.7em; padding: 3px 9px; border-radius: 20px; font-weight: 600; white-space: nowrap; }}
    .high {{ background: #ffe0e0; color: #c0392b; }}
    .medium {{ background: #fff3e0; color: #e67e22; }}
    .low {{ background: #e8f5e9; color: #27ae60; }}
    a {{ color: #4a90e2; text-decoration: none; }}
    footer {{ text-align: center; color: #aaa; font-size: 0.82em; padding: 20px 0 10px; }}
  </style>
</head>
<body>
  <header>
    <h1>🤖 AI ニュースまとめ</h1>
    <div class="date">{TODAY} | 国内 &amp; 世界のAI最新情報</div>
  </header>
  <div class="tab-container">
    <button class="tab-btn domestic active" onclick="switchTab('domestic')">🇯🇵 国内ニュース</button>
    <button class="tab-btn world" onclick="switchTab('world')">🌍 世界のニュース</button>
  </div>
  <div id="tab-domestic" class="tab-content active">
    {dom_html}
  </div>
  <div id="tab-world" class="tab-content">
    {wld_html}
  </div>
  <footer>Powered by Claude AI | 自動生成 | {TODAY}</footer>
  <script>
    function switchTab(tab) {{
      document.querySelectorAll('.tab-content').forEach(function(el) {{
        el.classList.remove('active');
      }});
      document.querySelectorAll('.tab-btn').forEach(function(el) {{
        el.classList.remove('active');
      }});
      document.getElementById('tab-' + tab).classList.add('active');
      document.querySelector('.tab-btn.' + tab).classList.add('active');
    }}
  </script>
</body>
</html>"""


def save_and_publish(html_content: str) -> str:
    os.makedirs("docs", exist_ok=True)

    filepath = f"docs/ai-news-{TODAY_FILE}.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    index_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=ai-news-{TODAY_FILE}.html">
  <title>AI ニュースまとめ</title>
</head>
<body>
  <p>最新レポートへ移動中... <a href="ai-news-{TODAY_FILE}.html">こちらをクリック</a></p>
</body>
</html>"""
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
    subprocess.run(["git", "add", "docs/"], check=True)
    subprocess.run(["git", "commit", "-m", f"Add AI news report {TODAY_FILE}"], check=True)
    subprocess.run(["git", "push"], check=True)

    repo_name = GITHUB_REPOSITORY.split("/")[-1] if "/" in GITHUB_REPOSITORY else "ai-news-bot"
    username = GITHUB_REPOSITORY.split("/")[0] if "/" in GITHUB_REPOSITORY else "user"
    page_url = f"https://{username}.github.io/{repo_name}/ai-news-{TODAY_FILE}.html"
    print(f"📄 GitHub Pages URL: {page_url}")
    return page_url


def send_email(page_url: str):
    print("メール送信中...")
    html_body = f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
  <div style="background:linear-gradient(135deg,#1a1a2e,#0f3460);color:white;padding:28px;border-radius:12px;margin-bottom:20px;">
    <h1 style="margin:0;font-size:1.5em;">🤖 AI ニュースまとめ</h1>
    <p style="margin:8px 0 0;opacity:0.8;">{TODAY}</p>
  </div>
  <p style="font-size:1.1em;color:#333;">本日のAIニュースレポートが完成しました。</p>
  <div style="text-align:center;margin:28px 0;">
    <a href="{page_url}" style="background:#0f3460;color:white;padding:14px 32px;border-radius:8px;text-decoration:none;font-size:1.1em;font-weight:bold;">
      📰 レポートを開く
    </a>
  </div>
  <p style="color:#888;font-size:0.85em;text-align:center;">Powered by Claude AI | 自動生成</p>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 AI ニュースまとめ {TODAY}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = MAIL_TO
    msg.attach(MIMEText("本日のAIニュースレポート: " + page_url, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    password_clean = GMAIL_APP_PASSWORD.encode('ascii', errors='ignore').decode('ascii').replace(' ', '')
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, password_clean)
        server.sendmail(GMAIL_USER, MAIL_TO, msg.as_string())
    print(f"✅ メール送信完了 → {MAIL_TO}")


def main():
    print(f"=== AI ニュースまとめ生成開始 {TODAY} ===")
    print("国内ニュースを収集中...")
    domestic = fetch_news(PROMPT_DOMESTIC)
    print("世界のニュースを収集中...")
    world = fetch_news(PROMPT_WORLD)
    print("HTMLを生成中...")
    html = build_html(domestic, world)
    page_url = save_and_publish(html)
    send_email(page_url)
    print("=== 完了 ===")


if __name__ == "__main__":
    main()
