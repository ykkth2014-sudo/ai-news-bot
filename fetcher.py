"""
fetcher.py - ニュース収集・記事本文取得モジュール
"""

import json
import urllib.request
import anthropic


CATEGORIES = ["モデル技術", "ビジネス", "規制政策", "製品ツール"]


def _call_claude(client: anthropic.Anthropic, prompt: str) -> str:
    """Claude API を呼び出してテキストを返す（web_search対応マルチターン）"""
    messages = [{"role": "user", "content": prompt}]

    while True:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages
        )

        # テキストブロックを収集
        text = ""
        for block in message.content:
            if block.type == "text":
                text += block.text

        # stop_reason が "end_turn" ならテキストを返す
        if message.stop_reason == "end_turn":
            return text

        # web_search ツールが使われた場合はアシスタント応答を履歴に追加して続行
        if message.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": message.content})
            # tool_result を作成（web_search は Anthropic が自動実行するので内容は空でOK）
            tool_results = []
            for block in message.content:
                if block.type == "tool_use":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": ""
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            # 予期しない stop_reason の場合はそのまま返す
            return text


def _parse_json(text: str) -> dict:
    """テキストからJSONを抽出してパース"""
    if not text or text.strip() == "":
        raise ValueError("APIからのレスポンスが空です。APIキーやレート制限を確認してください。")

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    # JSON部分だけ抽出（{ から始まる部分）
    start = text.find("{")
    if start != -1:
        text = text[start:]
    return json.loads(text)


def fetch_article_text(url: str, max_chars: int = 2000) -> str:
    """URLから記事本文を取得する（失敗時は空文字を返す）"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AI-News-Bot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode("utf-8", errors="ignore")

        import re
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


def summarize_article(client: anthropic.Anthropic, title: str, url: str, article_text: str) -> str:
    """記事本文をClaudeで要約する"""
    if not article_text:
        return "記事本文の取得に失敗しました。"

    prompt = f"""以下の記事を日本語で3〜5文に要約してください。
要約のみ出力し、前置きや説明は不要です。

タイトル: {title}
URL: {url}

記事本文:
{article_text}
"""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    for block in message.content:
        if block.type == "text":
            return block.text.strip()
    return ""


def fetch_news(client: anthropic.Anthropic, region: str, today: str) -> dict:
    """
    指定地域のニュースをJSON形式で取得する
    region: "domestic"（国内）または "world"（世界）
    """
    if region == "domestic":
        region_desc = "日本国内"
        exclude = ""
    else:
        region_desc = "世界（米国・欧州・中国など）"
        exclude = "日本のニュースは除外し、海外のニュースのみを対象としてください。"

    prompt = f"""あなたは優秀なAIニュースキュレーターです。
今日（{today}）の{region_desc}の最新AIニュースをウェブ検索で調査してください。
{exclude}

以下の4カテゴリで合計10件以上のニュースをJSON形式で出力してください。
カテゴリ：モデル技術、ビジネス、規制政策、製品ツール

出力形式（JSONのみ、説明文・コードブロック不要）：
{{
  "categories": [
    {{
      "name": "モデル技術",
      "summary": "このカテゴリの1〜2行の概要",
      "items": [
        {{
          "title": "ニュースタイトル（日本語）",
          "url": "情報源の実在するURL",
          "importance": "高"
        }}
      ]
    }}
  ]
}}

importanceは「高」「中」「低」のいずれか。
各カテゴリ最低2件以上。合計10件以上必須。
URLは実在するものを必ず記載すること。
"""

    print(f"  [{region}] ニュース一覧を取得中...")
    text = _call_claude(client, prompt)
    data = _parse_json(text)

    # 各記事の本文を取得して要約
    for category in data["categories"]:
        for item in category["items"]:
            url = item.get("url", "")
            title = item.get("title", "")
            print(f"  [{region}] 記事を取得・要約中: {title[:30]}...")
            article_text = fetch_article_text(url)
            summary = summarize_article(client, title, url, article_text)
            item["body"] = summary

    return data
