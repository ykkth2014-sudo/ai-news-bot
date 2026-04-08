"""
mailer.py - メール送信モジュール
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send(gmail_user: str, gmail_app_password: str, mail_to: str, page_url: str, today: str):
    """
    GitHub Pages のリンクをメールで送信する
    """
    html_body = f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
  <div style="background:linear-gradient(135deg,#1a1a2e,#0f3460);color:white;padding:28px;border-radius:12px;margin-bottom:20px;">
    <h1 style="margin:0;font-size:1.5em;">🤖 AI ニュースまとめ</h1>
    <p style="margin:8px 0 0;opacity:0.8;">{today}</p>
  </div>
  <p style="font-size:1.1em;color:#333;margin-bottom:20px;">
    本日のAIニュースレポートが完成しました。<br>
    国内・世界のAI最新情報をまとめています。
  </p>
  <div style="text-align:center;margin:28px 0;">
    <a href="{page_url}"
       style="background:#0f3460;color:white;padding:14px 32px;border-radius:8px;
              text-decoration:none;font-size:1.1em;font-weight:bold;display:inline-block;">
      📰 レポートを開く
    </a>
  </div>
  <p style="color:#888;font-size:0.85em;text-align:center;margin-top:20px;">
    Powered by Claude AI | 自動生成
  </p>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 AI ニュースまとめ {today}"
    msg["From"]    = gmail_user
    msg["To"]      = mail_to
    msg.attach(MIMEText(f"本日のAIニュースレポート:\n{page_url}", "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # パスワードのASCII以外の文字を除去
    password_clean = gmail_app_password.encode("ascii", errors="ignore").decode("ascii").replace(" ", "")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, password_clean)
        server.sendmail(gmail_user, mail_to, msg.as_string())

    print(f"  メール送信完了 → {mail_to}")
