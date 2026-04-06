# 🤖 AI ニュース自動生成ボット

毎朝6時（JST）に Claude AI が国内・世界のAIニュースをHTMLレポートにまとめ、メールで届けます。

---

## セットアップ手順

### 1. GitHubにシークレットを登録する

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** から以下を登録：

| シークレット名 | 内容 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic APIキー（`sk-ant-...`） |
| `GMAIL_USER` | 送信元GmailアドレS（例: yourname@gmail.com） |
| `GMAIL_APP_PASSWORD` | Gmailアプリパスワード（16文字） |
| `MAIL_TO` | 受信先メールアドレス |

### 2. Gmailアプリパスワードの取得方法

1. Googleアカウントの **セキュリティ設定** を開く
2. **2段階認証を有効化**（必須）
3. 検索欄に「アプリパスワード」と入力
4. アプリ名を「AI News Bot」などと入力して「作成」
5. 表示された16文字をコピーして `GMAIL_APP_PASSWORD` に登録

### 3. 動作確認（手動実行）

GitHub の **Actions タブ** → `AI ニュース自動生成` → **Run workflow** ボタンで今すぐ実行できます。

---

## 自動実行スケジュール

毎朝 **6:00 JST** に自動実行されます（GitHub Actions の cron: `0 21 * * *`）。

---

## ファイル構成

```
ai-news-bot/
├── .github/
│   └── workflows/
│       └── ai-news.yml   # GitHub Actions 設定
├── generate_news.py       # メインスクリプト
└── README.md
```
