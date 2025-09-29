# utilsディレクトリ ユーティリティスクリプト マニュアル

## 概要
`utils/`ディレクトリには、NCVスペシャルモニターシステムで使用する各種ユーティリティスクリプトが格納されています。これらはすべてスタンドアロン実行可能で、システムの補助機能を提供します。

---

## extract_comments.py
### 機能
データベースから特定ユーザーのコメントをランダムに抽出してテキストファイルに保存

### 使用方法
```bash
python utils/extract_comments.py
```

### 主要機能
- `extract_random_comments(user_id, num_comments=100)` - 指定ユーザーIDのコメントをランダムに取得
- `save_comments_to_file(comments, filename)` - コメントをテキストファイルに保存
- デフォルト: ユーザーID "21639740" のコメント100件を抽出

### 出力
`user_{user_id}_comments.txt` ファイルにコメントを保存

---

## JsonStepper.py
### 機能
JSONファイルの値を段階的にクリップボードにコピーするGUIツール

### 使用方法
```bash
python utils/JsonStepper.py
```

### 主要機能
- JSONファイル読み込み（ファイルダイアログ）
- 最大10段階の階層キー入力対応
- 「次」ボタンで順番に値をクリップボードにコピー
- 右側テキストボックスで履歴表示

### 使用例
1. 「JSONファイルを開く」でファイル選択
2. キー欄に階層を入力（例: `data.users.0.name`）
3. 「スタート」→「次」で値を順次コピー

---

## name_extractor.py
### 機能
ニコニコ動画のユーザーIDからユーザー名を取得

### 使用方法
```bash
python utils/name_extractor.py
# または関数として
from utils.name_extractor import fetch_nico_user_name
name = fetch_nico_user_name("8908639")
```

### 主要機能
- `fetch_nico_user_name(user_id)` - ユーザーIDからユーザー名を取得
- 3つの抽出方法：
  1. metaタグ（`profile:username`）
  2. JSON-LD構造化データ
  3. CSSクラス名（`UserDetailsHeader-nickname`）

### デフォルト設定
テスト用ユーザーID: "8908639"

---

## QueryRefinerRAG.py
### 機能
AIクライアント（OpenAI/Google）を使用したRAG検索システム

### 使用方法
```bash
python utils/QueryRefinerRAG.py "この人なにが好き？"
# または引数なしでデフォルト質問
python utils/QueryRefinerRAG.py
```

### 主要機能
- **AIクライアント対応**: OpenAI (GPT-4o/4o-mini), Google (Gemini-2.5-flash)
- **RAG検索**: ベクトル類似度検索でコメントを取得
- **コンテキスト生成**: 検索結果から回答を生成
- **設定自動読み込み**: `config/ncv_special_config.json`からAPIキー取得

### 設定要件
- OpenAI API キーまたは Google API キー
- ベクトル化済みデータベース（`data/vectors.db`）

---

## vectorize_existing_data.py
### 機能
既存のデータベースのコメントをベクトル化してRAGシステム用に準備

### 使用方法
```bash
python utils/vectorize_existing_data.py
```

### 主要機能
- **ベクトルDB初期化**: `data/vectors.db`の作成とテーブル設定
- **コメントベクトル化**: OpenAI APIでembeddingを生成
- **AI分析ベクトル化**: 分析結果もベクトル化
- **バッチ処理**: 既存データを一括処理
- **進捗表示**: 処理状況とステータス表示

### 実行前提
- OpenAI API キーの設定
- `data/ncv_monitor.db`にコメントデータが存在

### 出力
- `data/vectors.db` - ベクトル化されたデータベース
- 処理状況とベクトル化件数の表示

---

## 共通の注意事項

### 依存関係
- 各スクリプトは独立して実行可能
- 一部のスクリプトは追加パッケージが必要（`pyperclip`, `openai`, `selenium`等）

### 設定ファイル
多くのスクリプトが以下の設定ファイルを参照：
- `config/ncv_special_config.json` - API キー等の設定

### データベース
以下のデータベースファイルを使用：
- `data/ncv_monitor.db` - メインデータベース
- `data/vectors.db` - ベクトル化データベース