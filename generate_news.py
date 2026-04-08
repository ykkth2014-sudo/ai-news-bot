#!/usr/bin/env python3
"""
generate_news.py - AI ニュースまとめ自動生成（メインスクリプト）

実行フロー:
  1. fetcher  : 国内・世界のニュースを収集し、各記事を要約
  2. builder  : HTML レポートを生成
  3. publisher: GitHub Pages に公開
  4. mailer   : メールでリンクを送信
"""

import os
import anthropic
from datetime import datetime, timezone, timedelta

import fetcher
import builder
import publisher
import mailer

# ── 設定 ──────────────────────────────────────────────
JST        = timezone(timedelta(hours=9))
TODAY      = datetime.now(JST).strftime("%Y年%m月%d日")
TODAY_FILE = datetime.now(JST).strftime("%Y-%m-%d")

ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
MAIL_TO            = os.environ["MAIL_TO"]
GITHUB_REPOSITORY  = os.environ.get("GITHUB_REPOSITORY", "")
# ─────────────────────────────────────────────────────


def main():
    print(f"=== AI ニュースまとめ生成開始 {TODAY} ===")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: ニュース収集・記事要約
    print("\n[Step 1] 国内ニュースを収集・要約中...")
    domestic = fetcher.fetch_news(client, "domestic", TODAY)

    print("\n[Step 1] 世界のニュースを収集・要約中...")
    world = fetcher.fetch_news(client, "world", TODAY)

    # Step 2: HTML生成
    print("\n[Step 2] HTMLレポートを生成中...")
    html = builder.build_html(domestic, world, TODAY)

    # Step 3: GitHub Pagesに公開
    print("\n[Step 3] GitHub Pagesに公開中...")
    page_url = publisher.publish(html, TODAY_FILE, GITHUB_REPOSITORY)

    # Step 4: メール送信
    print("\n[Step 4] メールを送信中...")
    mailer.send(GMAIL_USER, GMAIL_APP_PASSWORD, MAIL_TO, page_url, TODAY)

    print(f"\n=== 完了 ===")
    print(f"レポートURL: {page_url}")


if __name__ == "__main__":
    main()
