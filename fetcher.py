"""
fetcher.py - ニュース収集・記事本文取得モジュール
"""

import json
import urllib.request
import anthropic


CATEGORIES = ["モデル技術", "ビジネス", "規制政策", "製品ツール"]


def _call_claude_with_search(client: anthropic.Anthropic, prompt: str) -> str:
    """
    web_search ツール付きで Claude を呼び出す（マルチターン対応）
    tool_use → tool_result → end_turn のループを処理する
    """
    messages = [{"role": "user", "content": prompt}]
    MAX_TURNS = 10  # 無限ループ防止

    for _ in range(MAX_TURNS):
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages
        )

        print(f"    [debug] stop_reason={message.stop_reason}, blocks={[b.type for b in message.content]}")

        # アシスタントの応答を履歴に追加
        messages.append({"role": "assistant", "content": message.content})

        if message.stop_reason == "end_turn":
            # テキストブロックを結合して返す
            text = ""
            for block in message.content:
                if block.type == "text":
                    text += block.text
            return text

        if message.stop_reason == "tool_use":
            # tool_result を作成して次のターンへ
            tool_results = []
            for block in message.content:
                if block.type == "tool_use":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": ""  # web_search は Anthropic が自動実行
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            # 予期しない stop_reason
            text = ""
            for block in message.content:
                if block.type == "text":
                    text += block.text
            return text

    raise RuntimeError("_call_claude_with_search: MAX_TURNS に達しました")


def _call_claude_simple(client: anthropic.Anthropic, prompt: str) -> str:
    """web_search なしのシンプルな Claude 呼び出し"""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}]
    )
    text = ""
    for block in message.content:
        if block.type == "text":
            text += block.text
    return text


def _parse_json(text: str) -> dict:
    """テキストからJSONを抽出してパース"""
    if not text or text.strip() == "":
        raise ValueError("APIからのレスポンスが空です。APIキーやレート制限を確認してください。")

    print(f"    [debug] _parse_json 受信テキスト先頭200字: {repr(text[:200])}")

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

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
    return _call_claude_simple(client, prompt)


def fetch_news(client: anthropic.Anthropic, region: str, today: str) -> dict:
    """
    指定地域のニュースをJSON形式で取得する
    region: "domestic"（国内）または "world"（世界）
    まず web_search 付きで試み、失敗したら web_search なしにフォールバック
    """
    if region == "domestic":
        region_desc = "日本国内"
        exclude = ""
    else:
        region_desc = "世界（米国・欧州・中国など）"
        exclude = "日本のニュースは除外し、海外のニュースのみを対象としてください。"

    prompt = f"""あなたは優秀なAIニュースキュレーターです。
今日（{today}）の{region_desc}の最新AIニュースを調査してください。
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

    print(f"  [{region}] ニュース一覧を取得中（web_search あり）...")
    try:
        text = _call_claude_with_search(client, prompt)
        data = _parse_json(text)
    except Exception as e:
        print(f"  [{region}] web_search あり失敗: {e}")
        print(f"  [{region}] web_search なしでリトライ中...")
        text = _call_claude_simple(client, prompt)
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
