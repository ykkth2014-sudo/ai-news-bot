"""
builder.py - HTMLレポート生成モジュール
"""


def _importance_badge(imp: str) -> str:
    cls = {"高": "high", "中": "medium", "低": "low"}.get(imp, "low")
    label = imp if imp in ["高", "中", "低"] else "低"
    return f'<span class="badge {cls}">{label}</span>'


def _render_section(data: dict, accent_color: str) -> str:
    """カテゴリデータからHTMLセクションを生成"""
    html = '<div class="summary-grid">'
    for cat in data.get("categories", []):
        html += f"""
        <div class="summary-card">
          <strong>{cat.get('name', '')}</strong>
          <p>{cat.get('summary', '')}</p>
        </div>"""
    html += "</div>"

    for cat in data.get("categories", []):
        html += f"""
        <div class="category-section">
          <div class="category-title" style="color:{accent_color}">📁 {cat.get('name', '')}</div>"""
        for item in cat.get("items", []):
            badge = _importance_badge(item.get("importance", "低"))
            title = item.get("title", "")
            body = item.get("body", "")
            url = item.get("url", "#")
            html += f"""
          <details>
            <summary>{title} {badge}</summary>
            <div class="detail-content">
              <p>{body}</p>
              <p style="margin-top:10px"><a href="{url}" target="_blank">🔗 元の記事を読む</a></p>
            </div>
          </details>"""
        html += "</div>"
    return html


def build_html(domestic: dict, world: dict, today: str) -> str:
    """国内・世界のニュースデータからHTMLを生成する"""
    dom_html = _render_section(domestic, "#e74c3c")
    wld_html = _render_section(world, "#2980b9")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI ニュースまとめ - {today}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; background: #f0f2f5; }}
    header {{ background: linear-gradient(135deg, #1a1a2e, #0f3460); color: white; padding: 36px 32px; border-radius: 16px; margin-bottom: 28px; }}
    h1 {{ font-size: 1.9em; }}
    .date {{ opacity: 0.75; margin-top: 6px; }}
    .tab-container {{ display: flex; margin-bottom: 24px; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
    .tab-btn {{ flex: 1; padding: 16px; border: none; cursor: pointer; font-size: 1.05em; font-weight: 700; background: white; color: #888; transition: all 0.2s; }}
    .tab-btn.active.domestic {{ background: #e74c3c; color: white; }}
    .tab-btn.active.world {{ background: #2980b9; color: white; }}
    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(2,1fr); gap: 14px; margin-bottom: 24px; }}
    .summary-card {{ background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); border-left: 4px solid #e74c3c; }}
    #tab-world .summary-card {{ border-left-color: #2980b9; }}
    .summary-card strong {{ display: block; margin-bottom: 5px; font-size: 0.95em; }}
    .summary-card p {{ font-size: 0.85em; color: #555; line-height: 1.5; }}
    .category-section {{ background: white; border-radius: 14px; padding: 22px; margin-bottom: 18px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
    .category-title {{ font-size: 1.2em; font-weight: 700; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 2px solid #f0f2f5; }}
    details {{ border: 1px solid #e8e8e8; border-radius: 10px; margin-bottom: 8px; overflow: hidden; }}
    summary {{ padding: 13px 16px; cursor: pointer; font-weight: 600; font-size: 0.92em; list-style: none; display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
    summary::-webkit-details-marker {{ display: none; }}
    summary:hover {{ background: #fafafa; }}
    summary::after {{ content: "▼"; font-size: 0.7em; color: #aaa; }}
    details[open] summary::after {{ content: "▲"; }}
    .detail-content {{ padding: 16px 18px; border-top: 1px solid #f0f0f0; color: #444; line-height: 1.75; font-size: 0.9em; }}
    .badge {{ font-size: 0.7em; padding: 3px 9px; border-radius: 20px; font-weight: 600; white-space: nowrap; flex-shrink: 0; }}
    .high {{ background: #ffe0e0; color: #c0392b; }}
    .medium {{ background: #fff3e0; color: #e67e22; }}
    .low {{ background: #e8f5e9; color: #27ae60; }}
    a {{ color: #4a90e2; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    footer {{ text-align: center; color: #aaa; font-size: 0.82em; padding: 20px 0 10px; }}
  </style>
</head>
<body>
  <header>
    <h1>🤖 AI ニュースまとめ</h1>
    <div class="date">{today} | 国内 &amp; 世界のAI最新情報</div>
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
  <footer>Powered by Claude AI | 自動生成 | {today}</footer>
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
