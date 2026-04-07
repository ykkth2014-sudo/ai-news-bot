#!/usr/bin/env python3
"""
AI ニュースまとめ自動生成スクリプト
毎朝 Claude API を使って国内・世界のAIニュースをHTMLレポートにまとめ、メール送信する
"""

import anthropic
import smtplib
import os
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── 設定 ──────────────────────────────────────────────
JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST).strftime("%Y年%m月%d日")
TODAY_FILE = datetime.now(JST).strftime("%Y-%m-%d")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER        = os.environ["GMAIL_USER"]        # 送信元GmailアドレS
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"] # Gmailアプリパスワード
MAIL_TO           = os.environ["MAIL_TO"]           # 受信先メールアドレス
# ─────────────────────────────────────────────────────


PROMPT = f"""
あなたは優秀なAIニュースキュレーターです。
今日（{TODAY}）の最新AIニュースを、国内（日本）と世界に分けて調査し、
以下の条件でHTMLレポートを生成してください。

## 条件
- 国内ニュース：10件以上（モデル技術・ビジネス・規制政策・製品ツール の4カテゴリ）
- 世界のニュース：10件以上（同4カテゴリ）
- 各ニュースは details/summary タグで展開可能にする
- 重要度バッジ（高/中/低）を付ける
- 情報源URLを必ず記載する

## 出力形式
以下のHTMLテンプレートをそのまま使い、中身を埋めて完全なHTMLを出力してください。
HTMLのみ出力し、前後の説明文は不要です。

<!DOCTYPE html>
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
    .tab-btn {{ flex: 1; padding: 16px; border: none; cursor: pointer; font-size: 1.05em; font-weight: 700; background: white; color: #888; }}
    .tab-btn.active.domestic {{ background: #e74c3c; color: white; }}
    .tab-btn.active.world {{ background: #2980b9; color: white; }}
    .tab-content {{ display: none; }} .tab-content.active {{ display: block; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(2,1fr); gap: 14px; margin-bottom: 24px; }}
    .summary-card {{ background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
    .domestic-section .summary-card {{ border-left: 4px solid #e74c3c; }}
    .world-section .summary-card {{ border-left: 4px solid #2980b9; }}
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
  <header><h1>🤖 AI ニュースまとめ</h1><div class="date">{TODAY} | 国内 &amp; 世界のAI最新情報</div></header>
  <div class="tab-container">
    <button class="tab-btn domestic active" onclick="switchTab('domestic')">🇯🇵 国内ニュース</button>
    <button class="tab-btn world" onclick="switchTab('world')">🌍 世界のニュース</button>
  </div>
  <div id="tab-domestic" class="tab-content active domestic-section">
    <!-- 国内：サマリーグリッド＋4カテゴリ×3件以上 をここに -->
  </div>
  <div id="tab-world" class="tab-content world-section">
    <!-- 世界：サマリーグリッド＋4カテゴリ×3件以上 をここに -->
  </div>
  <footer>Powered by Claude AI | 自動生成 | {TODAY}</footer>
  <script>
    function switchTab(tab) {{
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById('tab-' + tab).classList.add('active');
      document.querySelector('.tab-btn.' + tab).classList.add('active');
    }}
  </script>
</body>
</html>
"""


def generate_html() -> str:
    """Claude API を呼んでHTMLを生成する"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print("Claude API にリクエスト送信中...")

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8192,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": PROMPT}]
    )

    # テキストブロックを結合
    html = ""
    for block in message.content:
        if block.type == "text":
            html += block.text

    # HTMLのみ抽出（```html ... ``` の場合に対応）
    if "```html" in html:
        html = html.split("```html")[1].split("```")[0].strip()
    elif "```" in html:
        html = html.split("```")[1].split("```")[0].strip()

    return html


def send_email(html_content: str):
    """GmailでHTMLメールを送信する"""
    print("メール送信中...")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 AI ニュースまとめ {TODAY}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = MAIL_TO

    # テキスト版（フォールバック）
    text_part = MIMEText("HTMLメールが表示されない場合はブラウザで開いてください。", "plain", "utf-8")
    html_part = MIMEText(html_content, "html", "utf-8")
    msg.attach(text_part)
    msg.attach(html_part)

    password_clean = GMAIL_APP_PASSWORD.encode('ascii', errors='ignore').decode('ascii').replace(' ', '')
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, password_clean)
        server.sendmail(GMAIL_USER, MAIL_TO, msg.as_string())

    print(f"✅ メール送信完了 → {MAIL_TO}")


def main():
    print(f"=== AI ニュースまとめ生成開始 {TODAY} ===")
    html = generate_html()

    # ファイル保存（デバッグ用）
    os.makedirs("output", exist_ok=True)
    filepath = f"output/ai-news-{TODAY_FILE}.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 HTMLファイル保存: {filepath}")

    send_email(html)
    print("=== 完了 ===")


if __name__ == "__main__":
    main()
