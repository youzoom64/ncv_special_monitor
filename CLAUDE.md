# NCV Special Monitor システム概要

## システム全体の構成

NCVスペシャルモニターシステムは、ニコニコ生放送の特定ユーザーを監視し、自動応答およびHTML出力を行うシステムです。主要な機能は以下の2つの流れで構成されています。

## 🔴 流れ1: リアルタイム応答システム（WebSocket）

### 中心ファイル
- `ncv_comment_monitor.py` - WebSocketサーバーメイン
- `config_manager.py` - 設定管理

### 処理の流れ
1. **WebSocketサーバー起動**
   - `NCVCommentServer`クラスがWebSocketサーバーを起動
   - クライアント（NCVプラグイン）からの接続を待機

2. **クライアント接続・認証**
   - `handle_hello()` - クライアント情報を受信・登録
   - instance_id、live_id、live_titleなどを管理

3. **コメント受信・処理**
   - `handle_comment()` - NCVプラグインからコメントを受信
   - 特別ユーザーかどうかをチェック（`monitored_user_ids`）
   - 設定に基づいて自動応答をトリガー

4. **自動応答送信**
   - `send_comment_to_specific_client()` - 特定のクライアントにコメント送信
   - `handle_send_comment_result()` - 送信結果の処理

### 主要な機能
- 特別ユーザー設定のリアルタイム読み込み
- WebSocketクライアント管理
- コメントの双方向通信
- 自動応答システム
- **スペシャルトリガー機能**（配信者に関係なく最優先で発火）
- **外部プログラム実行機能**（exe/bat/cmdファイルの自動実行）

## 🔵 流れ2: HTML生成システム（ファイル監視→パイプライン）

### 中心ファイル
- `file_monitor.py` - NCVフォルダ監視
- `processors/broadcast_detector.py` - 放送終了検出（移動済み）
- `pipeline.py` - パイプライン実行管理
- `processors/` - 各ステップの処理

### 処理の流れ

#### 1. ファイル監視フェーズ
**file_monitor.py**
- `NCVFolderMonitor`クラスがNCVフォルダを監視
- 新規XMLファイル（`ncvLog_lv*.xml`）を検出
- `_start_xml_monitoring()` - 監視開始とパイプライン準備

#### 2. 放送終了検出フェーズ
**processors/broadcast_detector.py**
- `BroadcastEndDetector`クラスが放送終了を監視
- ニコニコ生放送のAPIを定期的にチェック
- 放送終了確認後にパイプライン実行をトリガー

#### 3. パイプライン実行フェーズ
**pipeline.py**
- `PipelineExecutor`が以下のステップを順次実行：

**Step00: Profile Monitor** (`processors/step00_profile_monitor.py`)
- プロフィール情報の監視・更新

**Step01: XML Parser** (`processors/step01_xml_parser.py`)
- NCVのXMLファイルを解析
- コメントデータと放送情報を抽出

**Step02: Special User Filter** (`processors/step02_special_user_filter.py`)
- 特別ユーザーのコメントをフィルタリング
- 設定に基づいてユーザーを特定

**Step03: HTML Generator** (`processors/step03_html_generator.py`)
- 特別ユーザー用のHTMLページを生成
- JSONファイルとしてもデータを保存

**Step04: Database Storage** (`processors/step04_database_storage.py`)
- SQLiteデータベースにデータを保存
- ベクトル化処理の準備

## 📁 ディレクトリ構造（整理後）

```
ncv_special_monitor/
├── main.py                      # GUIアプリケーションエントリーポイント
├── ncv_comment_monitor.py       # WebSocketサーバー（リアルタイム応答）
├── file_monitor.py              # NCVフォルダ監視
├── pipeline.py                  # パイプライン実行管理
├── config_manager.py            # 設定管理（システム中核）
├── logger.py                    # ログ機能（システム中核）
├── main.bat                     # 実行用バッチファイル
├── ncv_comment_monitor.bat      # WebSocketサーバー起動用バッチ
├── requirements.txt             # Python依存関係
├── CLAUDE.md                    # システム概要（このファイル）
│
├── processors/                  # パイプライン各ステップ
│   ├── broadcast_detector.py    # 放送終了検出（移動済み）
│   ├── step00_profile_monitor.py
│   ├── step01_xml_parser.py
│   ├── step02_special_user_filter.py
│   ├── step03_html_generator.py
│   └── step04_database_storage.py
│
├── gui/                         # GUI関連
│   ├── __init__.py
│   ├── main_window.py           # メインGUIウィンドウ
│   ├── utils.py                 # GUI共通ユーティリティ
│   └── （その他GUIコンポーネント）
│
├── libs/                        # ライブラリ機能
│   ├── bulk_broadcaster_registration.py  # 一括配信者登録機能
│   └── specialuser_follow_fetcher.py     # フォロー情報取得
│
├── utils/                       # ユーティリティスクリプト
│   ├── README.md                # ユーティリティマニュアル
│   ├── extract_comments.py      # コメント抽出ツール
│   ├── JsonStepper.py           # JSON値段階コピーツール
│   ├── name_extractor.py        # ニコニコユーザー名取得
│   ├── QueryRefinerRAG.py       # RAG検索システム（新版）
│   └── vectorize_existing_data.py # データベクトル化ツール
│
├── unsorted/                    # 未整理・古いファイル
│   ├── main_old.py              # 古いメインファイル
│   ├── rag_system.py            # 古いRAGシステム
│   ├── rag/                     # 古いRAG関連ファイル
│   └── （その他移動済みファイル）
│
├── config/                      # 設定ファイル（gitignore）
│   ├── global_config.json       # グローバル設定
│   ├── ncv_special_config.json  # API設定（機密）
│   └── （その他設定ファイル）
│
├── data/                        # データベース（gitignore）
│   ├── ncv_monitor.db           # メインデータベース
│   └── vectors.db               # ベクトル化データベース
│
├── SpecialUser/                 # 特別ユーザー設定・出力（gitignore）
├── templates/                   # HTMLテンプレート
├── logs/                        # ログファイル
├── pipeline_test_output/        # パイプラインテスト出力
├── libs/                        # ライブラリファイル
├── rec/                         # 録画関連
└── venv/                        # Python仮想環境
```

## 🔗 システム間の連携

1. **設定共有**
   - `config_manager.py`が両システム間で設定を共有
   - 特別ユーザー設定は`SpecialUser/`ディレクトリで管理

2. **データ連携**
   - HTML生成システムで作成されたデータをデータベースに保存
   - リアルタイムシステムがデータベースの設定を参照

3. **ログ・GUI連携**
   - `gui/utils.py`の`log_to_gui()`で統一されたログ出力
   - 両システムの状態をGUIで監視可能

## 🚀 実行方法

### メインGUIアプリケーション（推奨）
```bash
python main.py
```

### WebSocketサーバー単体実行
```bash
python ncv_comment_monitor.py
# または
ncv_comment_monitor.bat
```

### バッチファイル実行
```bash
main.bat  # GUIアプリケーション起動
```

## ⚙️ 設定ファイル（config/ディレクトリ）

- `global_config.json` - グローバル設定
- `ncv_special_config.json` - API設定（OpenAI、Google APIキー等）
- `SpecialUser/{user_id}_{username}/config.json` - ユーザー別設定

## 📊 出力ファイル

- **HTMLファイル**: `SpecialUser/{user_id}_{username}/`
- **データベース**: `data/ncv_monitor.db`, `data/vectors.db`
- **ログファイル**: `logs/`
- **一時ファイル**: `pipeline_test_output/`

## 🔧 主要な依存関係

- **WebSocket通信**: `websockets`
- **HTTP通信**: `requests`（放送終了検出）
- **データベース**: `sqlite3`
- **GUI**: `tkinter`
- **並行処理**: `threading`
- **AI機能**: `openai`, `google.generativeai`
- **Web scraping**: `selenium`, `beautifulsoup4`

## 💡 開発・デバッグ時の注意点

1. **WebSocketサーバー**
   - ポート番号の競合に注意
   - クライアント接続状態の確認

2. **ファイル監視**
   - NCVフォルダパスの設定確認
   - XMLファイルの権限・アクセス状況

3. **パイプライン**
   - 各ステップの実行ログを確認
   - エラー時のデータ状態をチェック

4. **設定管理**
   - JSON設定ファイルの構文エラーに注意
   - ユーザー設定の有効/無効状態を確認
   - APIキーの適切な設定

5. **ファイル整理後の変更点**
   - `broadcast_detector.py` → `processors/broadcast_detector.py`
   - 各種ユーティリティ → `utils/`ディレクトリ
   - ライブラリ機能 → `libs/`ディレクトリ
   - 古いファイル → `unsorted/`ディレクトリ

## 🔒 セキュリティ考慮事項

- `config/`ディレクトリは`.gitignore`で除外（APIキー保護）
- `data/`ディレクトリは`.gitignore`で除外（データベース保護）
- `SpecialUser/`ディレクトリは`.gitignore`で除外（プライベートデータ保護）

## 📝 ユーティリティツール

`utils/`ディレクトリには各種補助ツールが格納されています。詳細は`utils/README.md`を参照してください。

- コメント抽出ツール
- JSON処理ツール
- ユーザー名取得ツール
- RAG検索システム
- データベクトル化ツール

## 🗃️ データベースビュー

### comments_with_broadcast ビュー

コメントデータと放送情報を簡単に取得するためのSQLビューです。

**作成済みビュー**：
```sql
CREATE VIEW comments_with_broadcast AS
SELECT
    c.*,
    b.lv_value as broadcast_lv_id,
    b.live_title as broadcast_title,
    b.start_time as broadcast_start_time
FROM comments c
JOIN broadcasts b ON c.broadcast_id = b.id;
```

**使用例**：
```python
# 特定ユーザーのコメントを放送情報と一緒に取得
cursor.execute("SELECT * FROM comments_with_broadcast WHERE user_id = ?", (user_id,))

# 特別ユーザーのコメントのみ取得
cursor.execute("SELECT * FROM comments_with_broadcast WHERE is_special_user = 1")
```

**取得可能な追加情報**：
- `broadcast_lv_id`: 放送ID（例：lv348354633）
- `broadcast_title`: 放送タイトル（例：始めてAI絵を覚えました）
- `broadcast_start_time`: 放送開始時間（UNIXタイムスタンプ）

**メリット**：
- JOINクエリを書く必要がない
- 既存の保存・取得ロジックは変更不要
- データの整合性が常に保持される
- コードが簡潔になる

## 🎯 スペシャルトリガー機能

### 概要

スペシャルトリガーは、**全配信者に共通して適用される最優先トリガー**です。通常のトリガーや反応回数制限を無視して、緊急時や特定の重要なキーワードに即座に反応できます。

### 特徴

1. **最優先実行**
   - 配信者トリガーより前にチェック
   - デフォルト応答より優先
   - 反応回数制限より前に評価

2. **`ignore_all_limits`機能**
   - `true`に設定すると、すべての反応回数制限を無視
   - 何度でも反応可能
   - 緊急通知などに最適

3. **配信者非依存**
   - どの配信者の放送でも発火
   - ユーザー単位で一元管理

4. **外部プログラム実行**
   - exe、bat、cmdファイルを自動実行
   - 変数置換対応
   - バックグラウンド実行

### 設定方法

**GUI操作：**
1. ユーザー編集画面を開く
2. 「スペシャルトリガーを有効化」にチェック
3. 「スペシャルトリガー管理」をクリック
4. トリガーを追加・編集

**設定項目：**
- **名前**: トリガーの識別名
- **キーワード**: 反応するキーワード（1行1つ）
- **条件**: OR（いずれか）/ AND（すべて）
- **応答タイプ**: 定型メッセージ / AI生成
- **発動確率**: 0-100%
- **全制限を無視**: 反応回数制限を無視
- **外部プログラム実行**: exe/batファイルの自動実行

### 外部プログラム実行機能

#### 設定手順

1. スペシャルトリガー編集画面で「外部プログラムを実行」にチェック
2. 「参照」ボタンで実行ファイルを選択
3. 必要に応じて引数を設定

#### 使用可能な変数

引数には以下の変数を使用できます：

- `{user_name}` - コメントしたユーザーの表示名
- `{user_id}` - ユーザーID
- `{comment}` - コメント内容
- `{live_id}` - 放送ID

**例：**
```
プログラムパス: C:\Tools\notify.exe
引数: --title "緊急通知" --user "{user_name}" --message "{comment}"
```

#### 実行仕様

- **非同期実行**: システムの動作をブロックしない
- **バックグラウンド実行**: ウィンドウを表示しない
- **エラーハンドリング**: 失敗時もシステムは継続動作
- **ログ出力**: 実行状況を`[EXTERNAL_PROGRAM]`タグでログ出力

### 動作の流れ

```
コメント受信
  ↓
ユーザー有効チェック
  ↓
【スペシャルトリガーチェック】← 最優先
  ├─ キーワードマッチ？
  ├─ 発動確率チェック
  ├─ 反応回数チェック（ignore_all_limitsで無視可能）
  └─ マッチした場合：
      ├─ 外部プログラム実行（設定時）
      └─ 応答メッセージ送信
  ↓
通常の反応回数制限チェック
  ↓
配信者トリガーチェック
  ↓
デフォルト応答
```

### 設定ファイル構造

```json
{
  "special_triggers_enabled": true,
  "special_triggers": [
    {
      "id": null,
      "name": "緊急通知",
      "enabled": true,
      "keywords": ["緊急", "助けて"],
      "keyword_condition": "OR",
      "response_type": "ai",
      "messages": ["緊急事態を検知しました"],
      "ai_response_prompt": "緊急事態として対応してください",
      "ignore_all_limits": true,
      "firing_probability": 100,
      "execute_program": true,
      "program_path": "C:/Tools/emergency_alert.exe",
      "program_args": "--user {user_name} --comment \"{comment}\""
    }
  ]
}
```

### 実装ファイル

- **GUI**: `gui/special_trigger_dialog.py` - 管理・編集画面
- **処理**: `ncv_comment_monitor.py` - トリガー判定・実行処理
- **設定**: `config_manager.py` - 設定の読み書き

### ログ出力例

```
[SPECIAL_TRIGGER] Matched special trigger: 緊急通知
[SPECIAL_TRIGGER] ignore_all_limits is enabled, bypassing all reaction limits
[EXTERNAL_PROGRAM] Executing: C:/Tools/emergency_alert.exe --user ようずん --comment "緊急"
[EXTERNAL_PROGRAM] Successfully launched: C:/Tools/emergency_alert.exe
[SPECIAL_TRIGGER] Generated response: 緊急事態を検知しました
```