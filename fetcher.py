"""
fetcher.py - ニュース収集・記事本文取得モジュール
"""

import json
import urllib.request
import anthropic


CATEGORIES = ["モデル技術", "ビジネス", "規制政策", "製品ツール"]


def _call_claude_with_search(client: anthropic.Anthropic, prompt: str) -> str:
    """web_search ツール付きで Claude を呼び出す（マルチターン対応）"""
    messages = [{"role": "user", "content": prompt}]
    MAX_TURNS = 10

    for _ in range(MAX_TURNS):
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages
        )

        print(f"    [debug] stop_reason={message.stop_reason}, blocks={[b.type for b in message.content]}")

        messages.append({"role": "assistant", "content": message.content})

        if message.stop_reason == "end_turn":
            text = ""
            for block in message.content:
                if block.type == "text":
                    text += block.text
            return text

        if message.stop_reason == "tool_use":
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
            text = ""
            for block in message.content:
                if block.type == "text":
                    text += block.text
            return text

    raise RuntimeError("MAX_TURNS に達しました")


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


def _extract_json(text: str) -> str:
    """テキストからJSON部分だけを抽出する"""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    start = text.find("{")
    if start != -1:
        text = text[start:]
    return text


def _parse_json(text: str) -> dict:
    """テキストからJSONを抽出してパース"""
    if not text or text.strip() == "":
        raise ValueError("レスポンスが空です")

    print(f"    [debug] レスポンス先頭200字: {repr(text[:200])}")

    extracted = _extract_json(text)
    if not extracted or not extracted.strip().startswith("{"):
        raise ValueError(f"JSONが見つかりません: {repr(text[:100])}")

    return json.loads(extracted)


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

    prompt = f"""以下の記事を日本語で3〜5文に要約してください。要約のみ出力してください。

タイトル: {title}
URL: {url}
記事本文: {article_text}
"""
    return _call_claude_simple(client, prompt)


def _build_prompt(region_desc: str, exclude: str) -> str:
    """ニュース取得プロンプトを生成する"""
    return f"""ウェブを検索して、{region_desc}の最新AIニュースを収集してください。
{exclude}

【重要】必ず以下のJSON形式のみで出力してください。説明文・前置き・コードブロック記号は一切不要です。
検索結果から実際に存在するニュースを選んでください。情報が不足していても、見つかった範囲でJSONを出力してください。

{{
  "categories": [
    {{
      "name": "モデル技術",
      "summary": "カテゴリの概要を1〜2行で",
      "items": [
        {{
          "title": "ニュースタイトル（日本語）",
          "url": "https://実在するURL",
          "importance": "高"
        }}
      ]
    }},
    {{
      "name": "ビジネス",
      "summary": "カテゴリの概要を1〜2行で",
      "items": []
    }},
    {{
      "name": "規制政策",
      "summary": "カテゴリの概要を1〜2行で",
      "items": []
    }},
    {{
      "name": "製品ツール",
      "summary": "カテゴリの概要を1〜2行で",
      "items": []
    }}
  ]
}}

importanceは「高」「中」「低」のいずれか。各カテゴリ2件以上、合計10件以上を目標にしてください。
"""


def _make_fallback_data(region_desc: str) -> dict:
    """取得失敗時のフォールバックデータを生成する"""
    return {
        "categories": [
            {"name": cat, "summary": f"{region_desc}の{cat}に関するニュースを取得できませんでした。", "items": []}
            for cat in CATEGORIES
        ]
    }


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
        exclude = "日本のニュースは除外し、海外のニュースのみ対象としてください。"

    prompt = _build_prompt(region_desc, exclude)

    # ① web_search ありで試みる
    print(f"  [{region}] ニュース一覧を取得中（web_search あり）...")
    try:
        text = _call_claude_with_search(client, prompt)
        data = _parse_json(text)
        print(f"  [{region}] web_search あり: 成功")
    except Exception as e:
        print(f"  [{region}] web_search あり失敗: {e}")

        # ② web_search なしでリトライ（今日の日付を外してリトライ）
        print(f"  [{region}] web_search なしでリトライ中...")
        prompt_no_date = _build_prompt(region_desc, exclude).replace(today, "最近")
        try:
            text = _call_claude_simple(client, prompt_no_date)
            data = _parse_json(text)
            print(f"  [{region}] web_search なし: 成功")
        except Exception as e2:
            print(f"  [{region}] web_search なしも失敗: {e2}")
            print(f"  [{region}] フォールバックデータを使用します")
            data = _make_fallback_data(region_desc)

    # 各記事の本文を取得して要約
    for category in data["categories"]:
        for item in category.get("items", []):
            url = item.get("url", "")
            title = item.get("title", "")
            if not url or not title:
                continue
            print(f"  [{region}] 記事を取得・要約中: {title[:30]}...")
            article_text = fetch_article_text(url)
            summary = summarize_article(client, title, url, article_text)
            item["body"] = summary

    return data
