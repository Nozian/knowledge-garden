# AI Knowledge Garden

複数のAIチャットサービスの対話ログを横断的に検索し、あなたの「第二の脳」を構築するWebアプリケーションです。

## 🌟 主な機能

- **ファイルアップロード**: ChatGPT、Claude、Geminiのログファイルをアップロード
- **高速検索**: キーワード検索とフィルター機能
- **チャット概要**: 最近の会話の自動要約表示
- **統計ダッシュボード**: メッセージ数、会話数、検索数の表示
- **モダンUI**: ガラスモーフィズム効果を使った美しいデザイン

## 🚀 技術スタック

### フロントエンド
- HTML5 + CSS3 + JavaScript (ES6+)
- レスポンシブデザイン
- ガラスモーフィズム効果

### バックエンド
- Flask 3.1.1
- Flask-CORS
- SQLAlchemy
- RESTful API

## 📦 インストール

### ローカル開発環境

1. リポジトリをクローン
```bash
git clone https://github.com/Nozian/knowledge-garden.git
cd knowledge-garden
```

2. 仮想環境を作成・有効化
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 依存関係をインストール
```bash
pip install -r requirements.txt
```

4. アプリケーションを起動
```bash
python src/main.py
```

5. ブラウザで http://localhost:5000 にアクセス

### Herokuデプロイ

1. Heroku CLIをインストール
2. Herokuにログイン
```bash
heroku login
```

3. Herokuアプリを作成
```bash
heroku create your-app-name
```

4. デプロイ
```bash
git push heroku main
```

## 📁 プロジェクト構造

```
ai-knowledge-garden/
├── src/
│   ├── main.py              # メインアプリケーション
│   ├── routes/
│   │   ├── user.py          # ユーザー関連API
│   │   └── knowledge.py     # AI Knowledge Garden API
│   ├── models/
│   │   └── user.py          # データベースモデル
│   ├── static/              # フロントエンドファイル
│   │   ├── index.html       # メインHTML
│   │   ├── style.css        # スタイルシート
│   │   └── script.js        # JavaScript
│   └── database/
│       └── app.db           # SQLiteデータベース
├── requirements.txt         # Python依存関係
├── Procfile                 # Heroku設定
├── runtime.txt              # Python バージョン
└── README.md                # このファイル
```

## 🔧 API エンドポイント

### ファイルアップロード
```
POST /api/upload
Content-Type: multipart/form-data
```

### 検索
```
POST /api/search
Content-Type: application/json
Body: {
  "query": "検索キーワード",
  "date_filter": "all|past_week|past_month|past_year",
  "speaker_filter": "all|user|assistant"
}
```

### 最近のチャット概要
```
GET /api/recent-chats
```

### 統計情報
```
GET /api/stats
```

## 🎨 デザイン特徴

- **ガラスモーフィズム**: 最新のデザイントレンド
- **グラデーション背景**: 美しい視覚効果
- **レスポンシブデザイン**: 全デバイス対応
- **アニメーション**: スムーズなユーザー体験

## 📄 ライセンス

MIT License

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します。

## 📞 サポート

質問やサポートが必要な場合は、GitHubのIssuesをご利用ください。

