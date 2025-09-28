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

## 🔵 流れ2: HTML生成システム（ファイル監視→パイプライン）

### 中心ファイル
- `file_monitor.py` - NCVフォルダ監視
- `broadcast_detector.py` - 放送終了検出
- `pipeline.py` - パイプライン実行管理
- `processors/` - 各ステップの処理

### 処理の流れ

#### 1. ファイル監視フェーズ
**file_monitor.py**
- `NCVFolderMonitor`クラスがNCVフォルダを監視
- 新規XMLファイル（`ncvLog_lv*.xml`）を検出
- `_start_xml_monitoring()` - 監視開始とパイプライン準備

#### 2. 放送終了検出フェーズ
**broadcast_detector.py**
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

## 📁 主要ディレクトリ構造

```
ncv_special_monitor/
├── ncv_comment_monitor.py      # WebSocketサーバー（リアルタイム応答）
├── file_monitor.py             # NCVフォルダ監視
├── broadcast_detector.py       # 放送終了検出
├── pipeline.py                 # パイプライン実行管理
├── config_manager.py           # 設定管理
├── processors/                 # パイプライン各ステップ
│   ├── step00_profile_monitor.py
│   ├── step01_xml_parser.py
│   ├── step02_special_user_filter.py
│   ├── step03_html_generator.py
│   └── step04_database_storage.py
├── gui/                        # GUI関連
├── config/                     # 設定ファイル
├── data/                       # データベース
├── SpecialUser/               # 特別ユーザー設定・出力
└── templates/                 # HTMLテンプレート
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

### リアルタイム応答システム
```bash
python ncv_comment_monitor.py
```

### ファイル監視・HTML生成システム
```bash
python main.py  # GUIアプリケーション起動
```

## ⚙️ 設定ファイル

- `config/global_config.json` - グローバル設定
- `SpecialUser/{user_id}_{username}/config.json` - ユーザー別設定
- `config/database_config.json` - データベース設定

## 📊 出力ファイル

- HTMLファイル: `SpecialUser/{user_id}_{username}/`
- データベース: `data/ncv_monitor.db`
- ログファイル: `logs/`
- 一時ファイル: `pipeline_test_output/`

## 🔧 主要な依存関係

- `websockets` - WebSocket通信
- `requests` - HTTP通信（放送終了検出）
- `sqlite3` - データベース
- `tkinter` - GUI
- `threading` - マルチスレッド処理

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