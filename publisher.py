"""
publisher.py - GitHub Pagesへの公開モジュール
"""

import os
import subprocess


def publish(html_content: str, today_file: str, github_repository: str) -> str:
    """
    HTMLをdocsフォルダに保存してGitにコミット・プッシュする
    Returns: GitHub Pages の公開URL
    """
    os.makedirs("docs", exist_ok=True)

    # 今日のレポートを保存
    filepath = f"docs/ai-news-{today_file}.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  HTMLファイル保存: {filepath}")

    # index.html を最新レポートへリダイレクト
    index_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=ai-news-{today_file}.html">
  <title>AI ニュースまとめ - 最新</title>
</head>
<body>
  <p>最新レポートへ移動中... <a href="ai-news-{today_file}.html">こちらをクリック</a></p>
</body>
</html>"""
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    # Git コミット＆プッシュ
    subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
    subprocess.run(["git", "add", "docs/"], check=True)
    subprocess.run(["git", "commit", "-m", f"Add AI news report {today_file}"], check=True)
    subprocess.run(["git", "push"], check=True)

    # GitHub Pages URL を生成
    if "/" in github_repository:
        username, repo_name = github_repository.split("/", 1)
    else:
        username, repo_name = "user", "ai-news-bot"

    page_url = f"https://{username}.github.io/{repo_name}/ai-news-{today_file}.html"
    print(f"  公開URL: {page_url}")
    return page_url
