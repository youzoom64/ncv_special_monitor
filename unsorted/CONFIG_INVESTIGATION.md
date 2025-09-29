# 設定ファイル調査記録

## 調査日: 2025-09-29

## 📄 調査対象: `config/config.json`

### ファイル内容
```json
{
  "ncv_special_config": "F:\\project_root\\app_workspaces\\ncv_special_monitor\\config\\ncv_special_config.json"
}
```

### 調査方法
1. `grep`を使用してPythonファイル内での使用箇所を検索
2. ディレクトリ全体でのファイル参照を調査
3. 類似する設定ファイルとの比較

### 調査結果
- ✅ **直接的な使用なし**: `config/config.json`を読み込んでいるPythonファイルは存在しない
- ✅ **間接的な使用もなし**: ファイルパスとして参照されている箇所もない

### 発見された類似ファイル
1. **`config/global_config.json`**
   - 使用箇所: `config_manager.py:14`
   - 用途: システム全体のグローバル設定

2. **`config/ncv_special_config.json`**
   - 使用箇所:
     - `vectorize_existing_data.py:27`
     - `QueryRefinerRAG.py:75`
     - `rag_system.py:24,128,412`
     - `specialuser_follow_fetcher.py:27`
   - 用途: RAG/AI/API設定、OpenAI APIキー管理

3. **`SpecialUser/{user_id}_{username}/config.json`**
   - 使用箇所:
     - `config_manager.py:660`
     - `processors/step00_profile_monitor.py:33`
     - `processors/step02_special_user_filter.py`
   - 用途: ユーザー別個別設定

### 推測される経緯
- `config/config.json`は`ncv_special_config.json`へのパス参照用として設計された可能性
- 実装時に直接パス指定方式に変更され、このファイルが不要になった
- 削除し忘れた未使用ファイルと判断される

### 結論
**`config/config.json`は未使用ファイルである**

### 推奨アクション
- [ ] ファイルの削除を検討
- [ ] または実際に使用するよう実装を修正
- [ ] 他の未使用設定ファイルの有無を調査

---

## 📄 調査対象: `config/global_config.json`

### ファイル内容（主要項目）
```json
{
  "ncv_folder_path": "C:\\Users\\youzo\\AppData\\Roaming\\posite-c\\NiconamaCommentViewer\\CommentLog",
  "monitor_enabled": true,
  "check_interval_minutes": 1,
  "retry_count": 3,
  "api_settings": {
    "summary_ai_model": "openai-gpt4o",
    "openai_api_key": "[APIキー]",
    "response_ai_model": "openai-gpt4o",
    "response_api_key": "[APIキー]",
    "response_default_prompt": "...",
    "response_max_characters": 300,
    "response_split_delay_seconds": 1,
    "analysis_system_prompt": "",
    "default_analysis_prompt": "..."
  },
  "default_broadcaster_config": { ... },
  "default_user_config": { ... }
}
```

### 調査結果
- ✅ **積極的に使用中**: システム全体で広く使用されている中核設定ファイル
- ✅ **明確な用途**: グローバル設定・API設定・デフォルト設定の管理

### 使用箇所と用途

#### 1. **config_manager.py** (設定管理の中核)
- `load_global_config()` - 設定読み込み
- `save_global_config()` - 設定保存
- `_safe_save_global_config()` - 安全な保存処理

#### 2. **file_monitor.py**
- **用途**: スキャン間隔設定の取得
- **項目**: `check_interval_minutes` (デフォルト5分)

#### 3. **ncv_comment_monitor.py** (WebSocketサーバー)
- **用途**: AI応答設定の取得
- **項目**:
  - `api_settings.response_ai_model`
  - `api_settings.response_api_key`
  - `api_settings.response_max_characters`
  - `api_settings.response_split_delay_seconds`

#### 4. **gui/main_window.py** (GUI設定)
- **用途**: GUI設定の読み込み・保存
- **項目**:
  - `ncv_folder_path`
  - `monitor_enabled`
  - `check_interval_minutes`

#### 5. **processors/step02_special_user_filter.py** (AI分析)
- **用途**: AI分析設定の取得
- **項目**: `api_settings.summary_ai_model`

#### 6. **デフォルト設定の提供**
- **ユーザー設定**: `default_user_config`
- **配信者設定**: `default_broadcaster_config`
- **分析モデル**: `default_analysis_model`

### 設定項目分析

#### **基本設定**
- `ncv_folder_path` - NCVログフォルダパス
- `monitor_enabled` - 監視有効/無効
- `check_interval_minutes` - チェック間隔（分）
- `retry_count` - リトライ回数

#### **API設定 (api_settings)**
- `summary_ai_model` - 要約AI用モデル
- `openai_api_key` - OpenAI APIキー
- `response_ai_model` - 応答AI用モデル
- `response_api_key` - 応答AI用APIキー
- `response_default_prompt` - デフォルト応答プロンプト
- `response_max_characters` - 応答最大文字数
- `response_split_delay_seconds` - 分割送信時の遅延
- `analysis_system_prompt` - 分析システムプロンプト
- `default_analysis_prompt` - デフォルト分析プロンプト

#### **デフォルト設定テンプレート**
- `default_broadcaster_config` - 配信者用デフォルト設定
- `default_user_config` - ユーザー用デフォルト設定

### 結論
**`config/global_config.json`はシステムの中核的な設定ファイルで、全機能で活用されている**

### 特記事項
- **セキュリティ注意**: APIキーがプレーンテキストで保存
- **設定の一元管理**: グローバル設定とデフォルト値が適切に分離
- **GUI連携**: 設定変更がGUIから可能

---

## 📄 調査対象: `config/ncv_special_config.json`

### ファイル内容（主要項目）
```json
{
  "ncv_folder_path": "C:/Users/youzo/AppData/Roaming/posite-c/NiconamaCommentViewer/CommentLog",
  "monitor_enabled": true,
  "check_interval_minutes": 5,
  "retry_count": 3,
  "api_settings": {
    "summary_ai_model": "openai-gpt4o",
    "answer_ai_model": "google-gemini‑2.5-flas-lite",
    "query_ai_model": "google-gemini‑2.5-flash-lite",
    "embedding_model": "text-embedding-3-small",
    "openai_api_key": "[APIキー]",
    "google_api_key": "[APIキー]",
    "suno_api_key": "",
    "imgur_api_key": ""
  },
  "special_users_config": {
    "default_analysis_enabled": true,
    "default_analysis_ai_model": "openai-gpt4o",
    "default_analysis_prompt": "...",
    "users": {
      "21639740": { ... },
      "a:eg1u1fPVwtRmmuji": { ... }
    }
  }
}
```

### 調査結果
- ✅ **RAG/AI専用設定**: RAGシステムとベクトル化処理で使用
- ⚠️ **設定重複**: global_config.jsonと一部項目が重複
- 🔄 **移行中の可能性**: 旧システムの設定ファイルと推測

### 使用箇所と用途

#### 1. **QueryRefinerRAG.py** (RAGクエリ改良)
- **用途**: RAGシステムの設定読み込み
- **項目**: `api_settings.openai_api_key`
- `QueryRefinerRAG.py:75`

#### 2. **rag_system.py** (RAGシステム中核)
- **用途**: RAG検索とLLM応答生成
- **項目**: `api_settings.openai_api_key`
- `rag_system.py:24,128,412` (3箇所で使用)

#### 3. **vectorize_existing_data.py** (ベクトル化処理)
- **用途**: 既存データのベクトル化
- **項目**: `api_settings.openai_api_key`
- `vectorize_existing_data.py:27,80,289`

#### 4. **specialuser_follow_fetcher.py** (フォロー情報取得)
- **用途**: ニコニコ動画フォロー情報の取得
- `specialuser_follow_fetcher.py:27`

### 設定項目分析

#### **基本設定（重複項目）**
- `ncv_folder_path` - **⚠️ global_config.jsonと重複**
- `monitor_enabled` - **⚠️ global_config.jsonと重複**
- `check_interval_minutes` - **⚠️ global_config.jsonと重複**
- `retry_count` - **⚠️ global_config.jsonと重複**

#### **RAG専用API設定 (api_settings)**
- `summary_ai_model` - 要約AI用モデル
- `answer_ai_model` - RAG回答生成用モデル
- `query_ai_model` - クエリ改良用モデル
- `embedding_model` - ベクトル埋め込み用モデル
- `openai_api_key` - OpenAI APIキー
- `google_api_key` - Google APIキー
- `suno_api_key` - Suno APIキー（未使用）
- `imgur_api_key` - Imgur APIキー（未使用）

#### **特別ユーザー設定 (special_users_config)**
- `default_analysis_enabled` - デフォルト分析有効/無効
- `default_analysis_ai_model` - デフォルト分析AIモデル
- `default_analysis_prompt` - デフォルト分析プロンプト
- `users` - 個別ユーザー設定（2名分）

### 重複設定の問題

#### **global_config.json vs ncv_special_config.json**
| 設定項目 | global_config.json | ncv_special_config.json | 値の違い |
|---------|-------------------|------------------------|---------|
| `ncv_folder_path` | ✅ | ✅ | 同一 |
| `monitor_enabled` | ✅ | ✅ | 同一 |
| `check_interval_minutes` | 1分 | 5分 | **異なる** |
| `retry_count` | ✅ | ✅ | 同一 |
| `openai_api_key` | ✅ | ✅ | 同一 |

### 結論
**`config/ncv_special_config.json`は旧システムの設定ファイルで、RAG/AI機能のみで使用中**

### 特記事項
- **設定重複問題**: 基本設定がglobal_config.jsonと重複
- **限定的使用**: RAG/ベクトル化/AI分析機能のみで使用
- **移行の必要性**: 設定を統合するか役割を明確化する必要
- **unused API keys**: Suno、Imgur APIキーが設定されているが未使用

### 推奨アクション
- [ ] 重複設定の統合を検討
- [ ] RAG専用設定として役割を明確化
- [ ] 未使用APIキー項目の削除
- [ ] 設定ファイルの命名規則統一

---

## 📄 メッセージ設定の混乱問題調査

### ⚠️ 深刻な問題：定型メッセージとデフォルトメッセージの混在

現在のシステムには、類似した名前で異なる用途のメッセージ設定項目が複数存在し、混乱を引き起こしています。

### 🔍 **実際の応答システムの真実**

**ユーザーの報告**：`ncv_special_config.json`の`send_message`が実際に応答として使われている

**調査結果**：以下の複雑な経路が判明
1. **WebSocket応答システム**: `SpecialUser/{user_id}_{username}/config.json`を使用
2. **未実装のコメントシステム**: `send_message`をDBに保存するが実際の送信機能は未実装
3. **第3のシステム**: `comment_system.py`への言及があるが実在しない

**実際の動作フロー**：
```
ncv_special_config.json (trigger_conditions.enabled: true)
    ↓ 不明な経路（要調査）
    ↓ SpecialUser/{user_id}_{username}/config.json への反映
    ↓ WebSocket応答システムが読み込み
    ↓ 実際の応答送信
```

### 問題の設定項目一覧

#### **1. `messages` (配列形式)**
- **場所**: `global_config.json` → `default_broadcaster_config.messages`
- **用途**: 配信者用の定型応答メッセージ
- **例**: `[">>{{no}}こんにちは"]`
- **実装**: `ncv_comment_monitor.py:672`で参照

#### **2. `messages` (配列形式)**
- **場所**: `global_config.json` → `default_user_config.default_response.messages`
- **用途**: ユーザー用のデフォルト応答メッセージ（現在は空配列）
- **例**: `[]` (空)
- **実装**: `config_manager.py:319`で処理

#### **3. `send_message` (文字列形式)**
- **場所**: `config/ncv_special_config.json` → `special_users_config.users.{user_id}.send_message`
- **用途**: 特別ユーザー向けの自動送信メッセージ
- **例**: `">>{no} こんにちは、ユーザーID{user_id}の、{display_name}さん"`
- **実装**: `processors/step04_database_storage.py:286`でDB保存

#### **4. `send_messages` (配列形式) - ※廃止予定**
- **場所**: `main_old.py` (旧GUI)
- **用途**: 旧システムでの複数メッセージ管理
- **例**: `[f">>{'{no}'} こんにちは、{display_name}さん"]`
- **実装**: 旧コードで使用、現在は非推奨

#### **5. `ai_response_prompt` (AI応答用)**
- **場所**: 複数の設定ファイル
- **用途**: AI自動応答用のプロンプト
- **例**: `"{{display_name}}として親しみやすく挨拶してください"`

### メッセージ送信システムの実装場所

#### **A. リアルタイム応答システム (WebSocket)**
- **ファイル**: `ncv_comment_monitor.py`
- **関数**: `generate_response_message()` (line 665)
- **使用設定**:
  - `messages` (定型メッセージ配列)
  - `ai_response_prompt` (AI応答)
- **処理フロー**:
  1. `response_type`で応答タイプ判定 (`predefined` or `ai`)
  2. 定型の場合：`messages`配列からランダム選択
  3. AI応答の場合：`ai_response_prompt`でAI生成

#### **B. データベース保存システム**
- **ファイル**: `processors/step04_database_storage.py`
- **用途**: `send_message`をDBに保存（コメントシステム用）
- **使用設定**: `send_message` (文字列)

### 混乱の原因

#### **1. 命名の統一性欠如**
| 項目名 | 形式 | 用途 | システム |
|-------|------|------|---------|
| `messages` | 配列 | 定型応答 | WebSocket |
| `send_message` | 文字列 | 自動送信 | Pipeline |
| `send_messages` | 配列 | 旧システム | 廃止予定 |

#### **2. 設定場所の分散**
- **global_config.json**: デフォルト設定
- **ncv_special_config.json**: 特別ユーザー設定
- **ユーザー別config.json**: 個別設定

#### **3. 処理システムの分離**
- **WebSocket**: リアルタイム応答
- **Pipeline**: バッチ処理・DB保存
- **GUI**: 設定管理

### テンプレート変数の不統一

#### **変数形式の混在**
- `{{no}}` ←→ `{no}` (コメント番号)
- `{{user_name}}` ←→ `{user_name}` (ユーザー名)
- `{{display_name}}` ←→ `{display_name}` (表示名)

#### **置換処理の実装箇所**
- **WebSocket**: `ncv_comment_monitor.py:692-713`
- **Config作成**: `config_manager.py:322-328`

### 設定継承の複雑性

```
global_config.json (グローバルデフォルト)
    ↓ default_broadcaster_config.messages
    ↓ default_user_config.default_response.messages
config_manager.py (設定作成時)
    ↓ テンプレート変数置換
SpecialUser/{user_id}_{username}/config.json
    ↓ default_response.messages
ncv_comment_monitor.py (実行時)
    ↓ generate_response_message()
WebSocket応答
```

### 推奨される解決策

#### **1. 設定項目の統一**
- `messages` → 定型応答メッセージ（配列）
- `auto_message` → 自動送信メッセージ（文字列）
- `ai_prompt` → AI応答プロンプト（文字列）

#### **2. テンプレート変数の統一**
- `{{variable}}` 形式に統一
- 置換処理の一元化

#### **3. 設定場所の整理**
- **global_config.json**: 全体デフォルト
- **user_config.json**: ユーザー個別設定
- **ncv_special_config.json**: RAG専用設定

---

## 次回調査予定
- [ ] ユーザー別設定の構造調査
- [ ] 設定ファイル間の依存関係マップ作成
- [ ] 設定重複問題の解決策検討
- [ ] **メッセージ設定項目の統一実装**

## 調査者メモ
- 設定管理の一元化が必要かもしれない
- ファイルパスのハードコーディングが多数確認された
- 設定ファイルの命名規則が統一されていない
- **global_config.jsonは適切に設計・活用されている**
- **APIキーの暗号化検討が必要**
- **⚠️ 重複設定問題が深刻：ncv_special_config.jsonとglobal_config.jsonで設定が重複**
- **RAG機能は独立した設定ファイルを使用している**
- **🚨 メッセージ設定の混乱問題が最も深刻：命名不統一、処理分散、変数形式混在**