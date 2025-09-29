# config_manager_v4.py - 新しい階層構造対応
import json
import os
from pathlib import Path
from datetime import datetime
import uuid
import threading
import websocket
import time

class HierarchicalConfigManager:
    def __init__(self):
        self.config_root = Path("config")
        self.global_config_path = self.config_root / "global_config.json"
        self.processed_xmls_file = self.config_root / "processed_xmls.json"
        self.trigger_series_path = self.config_root / "trigger_series.json"

        # 設定ディレクトリ作成
        self.config_root.mkdir(exist_ok=True)

    def load_global_config(self) -> dict:
        """グローバル設定を読み込み"""
        if self.global_config_path.exists():
            with open(self.global_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # デフォルトグローバル設定
        default_config = {
            "ncv_folder_path": "C:\\Users\\youzo\\AppData\\Roaming\\posite-c\\NiconamaCommentViewer\\CommentLog",
            "monitor_enabled": True,
            "check_interval_minutes": 5,
            "retry_count": 3,
            "api_settings": {
                "summary_ai_model": "openai-gpt4o",
                "openai_api_key": "",
                "google_api_key": "",
                # AI反応設定
                "response_ai_model": "openai-gpt4o",
                "response_api_key": "",
                "response_default_prompt": "以下のコメントに対して、{{display_name}}として自然で親しみやすい返答をしてください。コメント: {{comment_content}}",
                "response_max_characters": 100,
                "response_split_delay_seconds": 1
            },
            "special_users_config": {
                "users": {}
            },
            "default_broadcaster_config": {
                "response_type": "predefined",
                "messages": [
                    ">>{{no}} こんにちは、{{broadcaster_name}}さん！",
                    ">>{{no}} {{broadcaster_name}}さんの配信楽しみにしてました！",
                    ">>{{no}} おつかれさまでした！"
                ],
                "ai_response_prompt": "{{broadcaster_name}}の配信に特化した親しみやすい返答をしてください",
                "max_reactions_per_stream": 1,
                "response_delay_seconds": 0
            },
            "default_user_config": {
                "description": "{{display_name}}さんの監視設定",
                "default_response": {
                    "response_type": "predefined",
                    "messages": [
                        ">>{{no}} こんにちは、{{display_name}}さん！",
                        ">>{{no}} {{display_name}}さん、お疲れ様です！"
                    ],
                    "ai_response_prompt": "{{display_name}}として親しみやすく挨拶してください",
                    "max_reactions_per_stream": 1,
                    "response_delay_seconds": 0
                }
            },
            "last_updated": datetime.now().isoformat()
        }

        self.save_global_config(default_config)
        return default_config

    def _safe_save_global_config(self, update_func):
        """汎用グローバル設定保存ロジック: 現在の設定を読み込み→更新関数適用→保存"""
        try:
            print(f"[DEBUG] _safe_save_global_config called")
            # ステップ1: 現在の完全な設定を読み込み
            current_config = self.load_global_config()
            print(f"[DEBUG] Loaded global config with keys: {list(current_config.keys())}")

            # ステップ2: 更新関数を適用
            print(f"[DEBUG] Applying global config update function...")
            update_func(current_config)

            # ステップ3: 完全な設定を保存
            print(f"[DEBUG] Saving global config...")
            current_config["last_updated"] = datetime.now().isoformat()
            with open(self.global_config_path, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, ensure_ascii=False, indent=2)
            print(f"[DEBUG] Global config save completed successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Global config save failed: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return False

    def save_global_config(self, config: dict):
        """グローバル設定を保存（メモリファースト方式）"""
        def update_global_config(current_config):
            # 新しい設定で現在の設定を更新
            current_config.update(config)

        success = self._safe_save_global_config(update_global_config)
        if not success:
            # フォールバック: 直接保存
            print(f"[WARNING] Using fallback global config save")
            config["last_updated"] = datetime.now().isoformat()
            with open(self.global_config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

    # 既存互換性のため
    def load_config(self):
        return self.load_global_config()

    def save_config(self, config: dict):
        self.save_global_config(config)

    # ユーザー管理
    def get_all_special_users(self) -> dict:
        """全スペシャルユーザーを取得（ディレクトリベースから）"""
        users = {}
        try:
            user_dirs = self.get_all_user_directories()
            for user_dir in user_dirs:
                user_id = user_dir["user_id"]
                display_name = user_dir["display_name"]

                # ディレクトリから設定を読み込み
                user_config = self.load_user_config_from_directory(user_id, display_name)

                # 旧形式のAPI互換性のために変換（enabledフラグも含める）
                users[user_id] = {
                    "user_id": user_id,
                    "display_name": display_name,
                    "enabled": user_config.get("user_info", {}).get("enabled", True),
                    "description": user_config.get("user_info", {}).get("description", ""),
                    "tags": user_config.get("user_info", {}).get("tags", []),
                    "ai_analysis": user_config.get("ai_analysis", {}),
                    "default_response": user_config.get("default_response", {}),
                    "broadcasters": user_config.get("broadcasters", {}),
                    "special_triggers": user_config.get("special_triggers", []),
                    "metadata": user_config.get("metadata", {})
                }
        except Exception as e:
            print(f"Error loading special users from directories: {str(e)}")

        return users

    def _safe_save_user_config(self, user_id: str, update_func):
        """汎用保存ロジック: 現在の設定を読み込み→更新関数適用→保存"""
        try:
            print(f"[DEBUG] _safe_save_user_config called for user {user_id}")
            # ステップ1: 現在の完全な設定を読み込み
            user_dirs = self.get_all_user_directories()
            print(f"[DEBUG] Found {len(user_dirs)} user directories")

            for user_dir in user_dirs:
                if user_dir["user_id"] == user_id:
                    display_name = user_dir["display_name"]
                    print(f"[DEBUG] Found user directory: {display_name}")
                    current_config = self.load_user_config_from_directory(user_id, display_name)
                    print(f"[DEBUG] Loaded config with keys: {list(current_config.keys())}")

                    # ステップ2: 更新関数を適用
                    print(f"[DEBUG] Applying update function...")
                    update_func(current_config)

                    # ステップ3: 完全な設定を保存
                    print(f"[DEBUG] Saving config to directory...")
                    self.save_user_config_to_directory(user_id, display_name, current_config)
                    self.notify_websocket_config_reload(user_id)
                    print(f"[DEBUG] Safe save completed successfully")
                    return True

            print(f"[DEBUG] User {user_id} not found in directories")
            return False
        except Exception as e:
            print(f"[ERROR] Safe save failed: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return False

    def get_user_config(self, user_id: str) -> dict:
        """特定のユーザー設定を取得（新しい形式を優先）"""
        # まず新しい場所から読み込みを試行
        try:
            user_dirs = self.get_all_user_directories()
            for user_dir in user_dirs:
                if user_dir["user_id"] == user_id:
                    display_name = user_dir["display_name"]
                    new_config = self.load_user_config_from_directory(user_id, display_name)

                    # 旧形式との互換性のために変換（enabledフラグも含める）
                    return {
                        "user_id": user_id,
                        "display_name": display_name,
                        "enabled": new_config.get("user_info", {}).get("enabled", True),
                        "description": new_config.get("user_info", {}).get("description", ""),
                        "tags": new_config.get("user_info", {}).get("tags", []),
                        "ai_analysis": new_config.get("ai_analysis", {}),
                        "default_response": new_config.get("default_response", {}),
                        "broadcasters": new_config.get("broadcasters", {}),
                        "special_triggers": new_config.get("special_triggers", []),
                        "metadata": new_config.get("metadata", {})
                    }
        except Exception as e:
            print(f"新しい形式での読み込みエラー ({user_id}): {str(e)}")

        # フォールバック：旧形式から読み込み
        # users = self.get_all_special_users()
        # return users.get(user_id, self.create_default_user_config(user_id))

    def save_user_config(self, user_id: str, user_config: dict):
        """ユーザー設定を保存"""
        # display_nameを取得（新旧両方の構造に対応）
        if "user_info" in user_config:
            display_name = user_config["user_info"].get("display_name", f"ユーザー{user_id}")
        else:
            display_name = user_config.get("display_name", f"ユーザー{user_id}")

        def update_user_config(config):
            if "user_info" in user_config:
                # 新形式からの更新
                if "user_info" in user_config:
                    config["user_info"].update(user_config["user_info"])
                if "ai_analysis" in user_config:
                    config["ai_analysis"].update(user_config["ai_analysis"])
                if "default_response" in user_config:
                    config["default_response"].update(user_config["default_response"])
                if "special_triggers" in user_config:
                    config["special_triggers"] = user_config["special_triggers"]
                # broadcasters は明示的に指定された場合のみ更新
                if "broadcasters" in user_config:
                    config["broadcasters"].update(user_config["broadcasters"])
            else:
                # 旧形式からの変換更新
                config["user_info"]["display_name"] = display_name
                config["user_info"]["description"] = user_config.get("description", "")
                config["user_info"]["tags"] = user_config.get("tags", [])
                if "ai_analysis" in user_config:
                    config["ai_analysis"].update(user_config["ai_analysis"])
                if "default_response" in user_config:
                    config["default_response"].update(user_config["default_response"])
                if "special_triggers" in user_config:
                    config["special_triggers"] = user_config["special_triggers"]

        success = self._safe_save_user_config(user_id, update_user_config)
        if not success:
            # フォールバック: 新規ユーザーの場合は直接作成
            print(f"[WARNING] Creating new user config for {user_id}")
            new_config = {
                "user_info": {
                    "user_id": user_id,
                    "display_name": display_name,
                    "description": user_config.get("description", ""),
                    "tags": user_config.get("tags", [])
                },
                "ai_analysis": user_config.get("ai_analysis", {
                    "enabled": True,
                    "model": "openai-gpt4o",
                    "use_default_prompt": True,
                    "custom_prompt": ""
                }),
                "default_response": user_config.get("default_response", {}),
                "broadcasters": user_config.get("broadcasters", {}),
                "special_triggers": user_config.get("special_triggers", []),
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "config_version": "5.0"
                }
            }
            self.save_user_config_to_directory(user_id, display_name, new_config)
            self.notify_websocket_config_reload(user_id)

    def delete_user_config(self, user_id: str):
        """ユーザー設定を削除（ディレクトリベース）"""
        try:
            # ユーザーディレクトリを特定
            user_dirs = self.get_all_user_directories()
            for user_dir in user_dirs:
                if user_dir["user_id"] == user_id:
                    display_name = user_dir["display_name"]
                    user_dir_path = self.get_user_directory_path(user_id, display_name)

                    # ディレクトリ全体を削除
                    import shutil
                    if user_dir_path.exists():
                        shutil.rmtree(user_dir_path)
                        print(f"ユーザー設定ディレクトリを削除: {user_dir_path}")
                    return

            print(f"ユーザー {user_id} のディレクトリが見つかりませんでした")
        except Exception as e:
            print(f"ユーザー設定削除エラー: {str(e)}")

    def create_default_user_config(self, user_id: str, display_name: str = None) -> dict:
        """デフォルトユーザー設定を作成（グローバル設定を使用）"""
        if display_name is None:
            display_name = f"ユーザー{user_id}"

        # グローバル設定からデフォルト値を取得
        global_config = self.load_global_config()
        default_user = global_config.get("default_user_config", {})

        # 説明文の置換
        description = default_user.get("description", "")
        description = description.replace("{{display_name}}", display_name)

        # デフォルトレスポンス設定
        default_response = default_user.get("default_response", {})

        # メッセージテンプレートを実際の名前で置換
        default_messages = default_response.get("messages", [])
        processed_messages = []
        for message in default_messages:
            processed_message = message.replace("{{display_name}}", display_name)
            processed_message = processed_message.replace("{{no}}", "{no}")
            processed_messages.append(processed_message)

        # AI応答プロンプトも置換
        ai_prompt = default_response.get("ai_response_prompt", f"{display_name}として親しみやすく挨拶してください")
        ai_prompt = ai_prompt.replace("{{display_name}}", display_name)

        return {
            "user_id": user_id,
            "display_name": display_name,
            "description": description,
            "tags": [],
            "ai_analysis": {
                "enabled": True,
                "model": "openai-gpt4o",
                "custom_prompt": "",
                "use_default_prompt": True
            },
            "default_response": {
                "response_type": default_response.get("response_type", "predefined"),
                "messages": processed_messages,
                "ai_response_prompt": ai_prompt,
                "max_reactions_per_stream": default_response.get("max_reactions_per_stream", 1),
                "response_delay_seconds": default_response.get("response_delay_seconds", 0)
            },
            "special_triggers": [],
            "broadcasters": {},
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "config_version": "4.0"
            }
        }

    # 配信者管理
    def get_user_broadcasters(self, user_id: str) -> dict:
        """ユーザーの配信者設定を取得"""
        user_config = self.get_user_config(user_id)
        return user_config.get("broadcasters", {})

    def save_broadcaster_config(self, user_id: str, broadcaster_id: str, broadcaster_config: dict):
        """配信者設定を保存"""
        def update_broadcaster(config):
            if "broadcasters" not in config:
                config["broadcasters"] = {}
            config["broadcasters"][broadcaster_id] = broadcaster_config

        success = self._safe_save_user_config(user_id, update_broadcaster)
        if not success:
            print(f"[WARNING] Fallback save for broadcaster {broadcaster_id}")
            user_config = self.get_user_config(user_id)
            if "broadcasters" not in user_config:
                user_config["broadcasters"] = {}
            user_config["broadcasters"][broadcaster_id] = broadcaster_config
            self.save_user_config(user_id, user_config)

    def delete_broadcaster_config(self, user_id: str, broadcaster_id: str):
        """配信者設定を削除"""
        def delete_broadcaster(config):
            broadcasters = config.get("broadcasters", {})
            if broadcaster_id in broadcasters:
                del broadcasters[broadcaster_id]

        success = self._safe_save_user_config(user_id, delete_broadcaster)
        if not success:
            print(f"[WARNING] Fallback delete for broadcaster {broadcaster_id}")
            user_config = self.get_user_config(user_id)
            broadcasters = user_config.get("broadcasters", {})
            if broadcaster_id in broadcasters:
                del broadcasters[broadcaster_id]
                self.save_user_config(user_id, user_config)

    def create_default_broadcaster_config(self, broadcaster_id: str, broadcaster_name: str = None) -> dict:
        """デフォルト配信者設定を作成（グローバル設定を使用）"""
        if broadcaster_name is None:
            broadcaster_name = f"配信者{broadcaster_id}"

        # グローバル設定からデフォルト値を取得
        global_config = self.load_global_config()
        default_broadcaster = global_config.get("default_broadcaster_config", {})

        # メッセージテンプレートを実際の配信者名で置換
        default_messages = default_broadcaster.get("messages", [f">>{'{no}'} {broadcaster_name}での挨拶です"])
        processed_messages = []
        for message in default_messages:
            # {{broadcaster_name}} を実際の配信者名に置換
            processed_message = message.replace("{{broadcaster_name}}", broadcaster_name)
            processed_message = processed_message.replace("{{no}}", "{no}")
            processed_messages.append(processed_message)

        # AI応答プロンプトも置換
        ai_prompt = default_broadcaster.get("ai_response_prompt", f"{broadcaster_name}の配信に特化した親しみやすい返答をしてください")
        ai_prompt = ai_prompt.replace("{{broadcaster_name}}", broadcaster_name)

        return {
            "broadcaster_id": broadcaster_id,
            "broadcaster_name": broadcaster_name,
            "enabled": True,
            "default_response": {
                "response_type": default_broadcaster.get("response_type", "predefined"),
                "messages": processed_messages,
                "ai_response_prompt": ai_prompt,
                "max_reactions_per_stream": default_broadcaster.get("max_reactions_per_stream", 1),
                "response_delay_seconds": default_broadcaster.get("response_delay_seconds", 0)
            },
            "triggers": []
        }

    # トリガー管理
    def get_broadcaster_triggers(self, user_id: str, broadcaster_id: str) -> list:
        """配信者のトリガー設定を取得"""
        user_config = self.get_user_config(user_id)
        broadcaster_config = user_config.get("broadcasters", {}).get(broadcaster_id, {})
        return broadcaster_config.get("triggers", [])

    def save_trigger_config(self, user_id: str, broadcaster_id: str, trigger_config: dict):
        """トリガー設定を保存"""
        print(f"[DEBUG] save_trigger_config called: user_id={user_id}, broadcaster_id={broadcaster_id}")
        print(f"[DEBUG] trigger_config: {trigger_config}")

        def update_trigger(config):
            print(f"[DEBUG] update_trigger called with config keys: {list(config.keys())}")

            if "broadcasters" not in config:
                config["broadcasters"] = {}
                print(f"[DEBUG] Created empty broadcasters section")

            if broadcaster_id not in config["broadcasters"]:
                config["broadcasters"][broadcaster_id] = self.create_default_broadcaster_config(broadcaster_id)
                print(f"[DEBUG] Created default broadcaster config for {broadcaster_id}")

            triggers = config["broadcasters"][broadcaster_id].get("triggers", [])
            print(f"[DEBUG] Current triggers count: {len(triggers)}")

            # IDが存在しない場合は生成
            if "id" not in trigger_config:
                trigger_config["id"] = str(uuid.uuid4())
                print(f"[DEBUG] Generated new trigger ID: {trigger_config['id']}")

            # 既存トリガーを更新、なければ追加
            trigger_found = False
            for i, trigger in enumerate(triggers):
                if trigger.get("id") == trigger_config["id"]:
                    triggers[i] = trigger_config
                    trigger_found = True
                    print(f"[DEBUG] Updated existing trigger at index {i}")
                    break

            if not trigger_found:
                triggers.append(trigger_config)
                print(f"[DEBUG] Added new trigger, total triggers: {len(triggers)}")

            config["broadcasters"][broadcaster_id]["triggers"] = triggers
            print(f"[DEBUG] Final triggers count: {len(config['broadcasters'][broadcaster_id]['triggers'])}")

        success = self._safe_save_user_config(user_id, update_trigger)
        print(f"[DEBUG] safe_save_user_config result: {success}")

        if not success:
            print(f"[WARNING] Fallback save for trigger {broadcaster_id}")
            user_config = self.get_user_config(user_id)
            if "broadcasters" not in user_config:
                user_config["broadcasters"] = {}
            if broadcaster_id not in user_config["broadcasters"]:
                user_config["broadcasters"][broadcaster_id] = self.create_default_broadcaster_config(broadcaster_id)

            triggers = user_config["broadcasters"][broadcaster_id].get("triggers", [])

            if "id" not in trigger_config:
                trigger_config["id"] = str(uuid.uuid4())

            trigger_found = False
            for i, trigger in enumerate(triggers):
                if trigger.get("id") == trigger_config["id"]:
                    triggers[i] = trigger_config
                    trigger_found = True
                    break

            if not trigger_found:
                triggers.append(trigger_config)

            user_config["broadcasters"][broadcaster_id]["triggers"] = triggers
            self.save_user_config(user_id, user_config)
            print(f"[DEBUG] Fallback save completed")

    def delete_trigger_config(self, user_id: str, broadcaster_id: str, trigger_id: str):
        """トリガー設定を削除"""
        def delete_trigger(config):
            broadcaster_config = config.get("broadcasters", {}).get(broadcaster_id, {})
            triggers = broadcaster_config.get("triggers", [])
            triggers = [t for t in triggers if t.get("id") != trigger_id]
            config["broadcasters"][broadcaster_id]["triggers"] = triggers

        success = self._safe_save_user_config(user_id, delete_trigger)
        if not success:
            print(f"[WARNING] Fallback delete for trigger {trigger_id}")
            user_config = self.get_user_config(user_id)
            broadcaster_config = user_config.get("broadcasters", {}).get(broadcaster_id, {})
            triggers = broadcaster_config.get("triggers", [])
            triggers = [t for t in triggers if t.get("id") != trigger_id]
            user_config["broadcasters"][broadcaster_id]["triggers"] = triggers
            self.save_user_config(user_id, user_config)

    def create_default_trigger_config(self, name: str = "新しいトリガー") -> dict:
        """デフォルトトリガー設定を作成"""
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "enabled": True,
            "keywords": ["こんにちは"],
            "keyword_condition": "OR",
            "response_type": "predefined",
            "messages": [f">>{'{no}'} こんにちは！"],
            "ai_response_prompt": "親しみやすく挨拶してください",
            "max_reactions_per_stream": 1,
            "response_delay_seconds": 0,
            "cooldown_minutes": 30,
            "firing_probability": 100
        }

    # スペシャルトリガー管理
    def get_user_special_triggers(self, user_id: str) -> list:
        """ユーザーのスペシャルトリガーを取得"""
        user_config = self.get_user_config(user_id)
        return user_config.get("special_triggers", [])

    def save_special_trigger_config(self, user_id: str, trigger_config: dict):
        """スペシャルトリガー設定を保存（汎用ロジック使用）"""
        def update_special_trigger(config):
            special_triggers = config.get("special_triggers", [])

            # IDが存在しない場合は生成
            if "id" not in trigger_config:
                trigger_config["id"] = str(uuid.uuid4())

            # 既存トリガーを更新、なければ追加
            trigger_found = False
            for i, trigger in enumerate(special_triggers):
                if trigger.get("id") == trigger_config["id"]:
                    special_triggers[i] = trigger_config
                    trigger_found = True
                    break

            if not trigger_found:
                special_triggers.append(trigger_config)

            config["special_triggers"] = special_triggers

        success = self._safe_save_user_config(user_id, update_special_trigger)
        if not success:
            # フォールバック
            user_config = self.get_user_config(user_id)
            special_triggers = user_config.get("special_triggers", [])
            if "id" not in trigger_config:
                trigger_config["id"] = str(uuid.uuid4())
            trigger_found = False
            for i, trigger in enumerate(special_triggers):
                if trigger.get("id") == trigger_config["id"]:
                    special_triggers[i] = trigger_config
                    trigger_found = True
                    break
            if not trigger_found:
                special_triggers.append(trigger_config)
            user_config["special_triggers"] = special_triggers
            self.save_user_config(user_id, user_config)

    def delete_special_trigger_config(self, user_id: str, trigger_id: str):
        """スペシャルトリガー設定を削除（汎用ロジック使用）"""
        def delete_special_trigger(config):
            special_triggers = config.get("special_triggers", [])
            special_triggers = [t for t in special_triggers if t.get("id") != trigger_id]
            config["special_triggers"] = special_triggers

        success = self._safe_save_user_config(user_id, delete_special_trigger)
        if not success:
            # フォールバック
            user_config = self.get_user_config(user_id)
            special_triggers = user_config.get("special_triggers", [])
            special_triggers = [t for t in special_triggers if t.get("id") != trigger_id]
            user_config["special_triggers"] = special_triggers
            self.save_user_config(user_id, user_config)

    # 処理済みXML管理（既存互換性）
    def load_processed_xmls(self):
        """処理済みXMLリストを読み込み"""
        try:
            if self.processed_xmls_file.exists():
                with open(self.processed_xmls_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get("processed_xmls", [])
        except Exception as e:
            print(f"処理済みXML読み込みエラー: {str(e)}")
        return []

    def save_processed_xmls(self, processed_list):
        """処理済みXMLリストを保存"""
        try:
            data = {
                "processed_xmls": processed_list,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.processed_xmls_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"処理済みXML保存エラー: {str(e)}")

    def add_processed_xml(self, xml_path):
        """処理済みXMLを追加"""
        processed_list = self.load_processed_xmls()
        if xml_path not in processed_list:
            processed_list.append(xml_path)
            self.save_processed_xmls(processed_list)

    def is_processed(self, xml_path):
        """XMLが処理済みかチェック"""
        processed_list = self.load_processed_xmls()
        return xml_path in processed_list

    # === 新しいスペシャルユーザーディレクトリ配下の設定管理 ===

    def get_user_directory_path(self, user_id: str, display_name: str = None) -> Path:
        """ユーザーディレクトリのパスを取得"""
        if display_name:
            dir_name = f"{user_id}_{display_name}"
        else:
            # display_nameがない場合は既存設定から取得を試行
            try:
                user_config = self.get_user_config(user_id)
                display_name = user_config.get("display_name", f"ユーザー{user_id}")
                dir_name = f"{user_id}_{display_name}"
            except:
                dir_name = f"{user_id}_Unknown"

        return Path("SpecialUser") / dir_name

    def get_user_config_path(self, user_id: str, display_name: str = None) -> Path:
        """ユーザー設定ファイルのパスを取得"""
        return self.get_user_directory_path(user_id, display_name) / "config.json"

    def load_user_config_from_directory(self, user_id: str, display_name: str = None) -> dict:
        """スペシャルユーザーディレクトリから設定を読み込み"""
        config_path = self.get_user_config_path(user_id, display_name)

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"ユーザー設定読み込みエラー ({config_path}): {str(e)}")

        # デフォルト設定を返す
        return self.create_default_user_config_structure(user_id, display_name)

    def save_user_config_to_directory(self, user_id: str, display_name: str, user_config: dict):
        """スペシャルユーザーディレクトリに設定を保存"""
        print(f"[DEBUG] save_user_config_to_directory called: user_id={user_id}, display_name={display_name}")
        print(f"[DEBUG] user_config keys: {list(user_config.keys())}")

        user_dir = self.get_user_directory_path(user_id, display_name)
        config_path = self.get_user_config_path(user_id, display_name)

        print(f"[DEBUG] Save path: {config_path}")

        # ディレクトリを作成
        user_dir.mkdir(parents=True, exist_ok=True)

        # メタデータを更新
        user_config["metadata"] = {
            "created_at": user_config.get("metadata", {}).get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "config_version": "5.0"
        }

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(user_config, f, ensure_ascii=False, indent=2)
            print(f"ユーザー設定保存: {config_path}")
            print(f"[DEBUG] 保存完了: {config_path}")
        except Exception as e:
            print(f"ユーザー設定保存エラー ({config_path}): {str(e)}")

    def create_default_user_config_structure(self, user_id: str, display_name: str = None) -> dict:
        """新しい形式のデフォルトユーザー設定を作成"""
        if not display_name:
            display_name = f"ユーザー{user_id}"

        # グローバル設定からデフォルト値を取得
        global_config = self.load_global_config()
        default_user_config = global_config.get("default_user_config", {})

        return {
            "user_info": {
                "user_id": user_id,
                "display_name": display_name,
                "description": "",
                "tags": []
            },
            "ai_analysis": {
                "enabled": True,
                "model": global_config.get("default_analysis_model", "openai-gpt4o"),
                "use_default_prompt": True,
                "custom_prompt": ""
            },
            "default_response": {
                "response_type": default_user_config.get("response_type", "predefined"),
                "messages": default_user_config.get("messages", [f">>{'{no}'} こんにちは、{display_name}さん"]),
                "ai_response_prompt": default_user_config.get("ai_response_prompt", f"{display_name}として親しみやすく挨拶してください"),
                "max_reactions_per_stream": default_user_config.get("max_reactions_per_stream", 1),
                "response_delay_seconds": default_user_config.get("response_delay_seconds", 0)
            },
            "broadcasters": {},
            "special_triggers": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "config_version": "5.0"
            }
        }

    def migrate_user_from_global_config(self, user_id: str):
        """グローバル設定からユーザー個別設定に移行"""
        # 既存のユーザー設定を取得
        old_user_config = self.get_user_config(user_id)
        display_name = old_user_config.get("display_name", f"ユーザー{user_id}")

        # 新しい形式に変換
        new_config = {
            "user_info": {
                "user_id": user_id,
                "display_name": display_name,
                "description": old_user_config.get("description", ""),
                "tags": old_user_config.get("tags", [])
            },
            "ai_analysis": old_user_config.get("ai_analysis", {
                "enabled": True,
                "model": "openai-gpt4o",
                "use_default_prompt": True,
                "custom_prompt": ""
            }),
            "default_response": old_user_config.get("default_response", {}),
            "broadcasters": old_user_config.get("broadcasters", {}),
            "special_triggers": old_user_config.get("special_triggers", []),
            "metadata": {
                "created_at": old_user_config.get("metadata", {}).get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
                "config_version": "5.0",
                "migrated_from_global": True
            }
        }

        # 新しい場所に保存
        self.save_user_config_to_directory(user_id, display_name, new_config)

        return new_config

    def get_all_user_directories(self) -> list:
        """すべてのスペシャルユーザーディレクトリを取得"""
        special_user_root = Path("SpecialUser")
        if not special_user_root.exists():
            return []

        user_dirs = []
        for item in special_user_root.iterdir():
            if item.is_dir() and "_" in item.name:
                try:
                    user_id_part = item.name.split("_")[0]
                    display_name_part = "_".join(item.name.split("_")[1:])
                    user_dirs.append({
                        "user_id": user_id_part,
                        "display_name": display_name_part,
                        "directory_name": item.name,
                        "path": item
                    })
                except:
                    continue

        return user_dirs

    # === トリガーシリーズ管理機能 ===

    def load_trigger_series(self) -> dict:
        """トリガーシリーズ設定を読み込み"""
        if self.trigger_series_path.exists():
            try:
                with open(self.trigger_series_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"トリガーシリーズ読み込みエラー: {str(e)}")
                return self._get_default_trigger_series()

        return self._get_default_trigger_series()

    def save_trigger_series(self, series_config: dict):
        """トリガーシリーズ設定を保存"""
        try:
            series_config["last_updated"] = datetime.now().isoformat()
            with open(self.trigger_series_path, 'w', encoding='utf-8') as f:
                json.dump(series_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"トリガーシリーズ保存エラー: {str(e)}")

    def _get_default_trigger_series(self) -> dict:
        """デフォルトのトリガーシリーズ設定"""
        default_series = {
            # 1. 親しみやすい挨拶シリーズ
            "friendly_greetings": {
                "name": "親しみやすい挨拶",
                "description": "温かくて親しみやすい挨拶メッセージのシリーズ",
                "triggers": [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "おはよう挨拶",
                        "enabled": True,
                        "keywords": ["おはよう", "おは", "グッモー", "good morning"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} おはようございます！今日も素敵な一日になりますように✨",
                            ">>{{no}} おはよう！今日も元気いっぱいで頑張ろう！",
                            ">>{{no}} おはようございます〜♪ いい天気ですね！"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 1,
                        "response_delay_seconds": 0,
                        "firing_probability": 100
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "こんばんは挨拶",
                        "enabled": True,
                        "keywords": ["こんばんは", "こんばんわ", "晩は", "お疲れ様"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} こんばんは！今日もお疲れ様でした〜",
                            ">>{{no}} こんばんは♪ ゆっくり過ごしてくださいね",
                            ">>{{no}} お疲れ様です！今夜もよろしくお願いします"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 1,
                        "response_delay_seconds": 0,
                        "firing_probability": 100
                    }
                ]
            },

            # 2. 機械的情報表示シリーズ
            "mechanical_info": {
                "name": "機械的情報表示",
                "description": "感情を排した冷静で機械的な情報提供メッセージ",
                "triggers": [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "時刻通知",
                        "enabled": True,
                        "keywords": ["時間", "何時", "いま何時", "時刻"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} システム時刻を確認してください。",
                            ">>{{no}} 現在時刻の確認が必要です。",
                            ">>{{no}} タイムスタンプ：確認要求を受信しました。"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 2,
                        "response_delay_seconds": 0,
                        "firing_probability": 100
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "状況報告",
                        "enabled": True,
                        "keywords": ["状況", "どう", "様子", "調子"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} システム稼働中。異常は検出されていません。",
                            ">>{{no}} ステータス：正常動作。監視継続中。",
                            ">>{{no}} 動作確認完了。全システム正常です。"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 2,
                        "response_delay_seconds": 0,
                        "firing_probability": 100
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "接続確認",
                        "enabled": True,
                        "keywords": ["接続", "つながってる", "見えてる", "聞こえる"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} 接続テスト実行中。信号受信を確認しました。",
                            ">>{{no}} 通信状態：良好。データ転送正常。",
                            ">>{{no}} 受信確認。接続は安定しています。"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 1,
                        "response_delay_seconds": 0,
                        "firing_probability": 100
                    }
                ]
            },

            # 3. お礼・感謝シリーズ
            "appreciation": {
                "name": "お礼・感謝表現",
                "description": "感謝やお礼を表現するメッセージシリーズ",
                "triggers": [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "ありがとう反応",
                        "enabled": True,
                        "keywords": ["ありがとう", "あざす", "thx", "thanks", "感謝"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} こちらこそありがとうございます！",
                            ">>{{no}} いえいえ、こちらこそ〜♪",
                            ">>{{no}} とんでもないです！ありがとうございます✨"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 2,
                        "response_delay_seconds": 0,
                        "firing_probability": 100
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "褒められ反応",
                        "enabled": True,
                        "keywords": ["すごい", "上手", "うまい", "素晴らしい", "great"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} ありがとうございます！嬉しいです〜",
                            ">>{{no}} そう言っていただけると励みになります！",
                            ">>{{no}} わー！ありがとうございます♪ 頑張った甲斐がありました！"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 1,
                        "response_delay_seconds": 0,
                        "firing_probability": 100
                    }
                ]
            },

            # 4. 雑談・コミュニケーションシリーズ
            "casual_chat": {
                "name": "雑談・コミュニケーション",
                "description": "日常的な雑談や軽いコミュニケーションのシリーズ",
                "triggers": [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "天気の話",
                        "enabled": True,
                        "keywords": ["天気", "雨", "晴れ", "曇り", "暑い", "寒い"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} 今日の天気はどうですか？",
                            ">>{{no}} 天気によって気分も変わりますよね〜",
                            ">>{{no}} こういう天気の日はのんびりしたいですね♪"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 2,
                        "response_delay_seconds": 0,
                        "firing_probability": 80
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "食べ物の話",
                        "enabled": True,
                        "keywords": ["美味しい", "食べた", "ご飯", "ランチ", "夕食", "おやつ"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} 美味しそう！何を食べたんですか？",
                            ">>{{no}} 食べ物の話って楽しいですよね〜",
                            ">>{{no}} お腹すいてきちゃいました😋"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 2,
                        "response_delay_seconds": 0,
                        "firing_probability": 70
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "趣味の話",
                        "enabled": True,
                        "keywords": ["趣味", "好き", "ハマってる", "最近", "始めた"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} 趣味の話って聞いてて楽しいです♪",
                            ">>{{no}} どんなことにハマってるんですか？",
                            ">>{{no}} 新しいことに挑戦するのっていいですよね！"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 1,
                        "response_delay_seconds": 0,
                        "firing_probability": 60
                    }
                ]
            },

            # 5. エモーショナル・応援シリーズ
            "emotional_support": {
                "name": "応援・励まし",
                "description": "励ましや応援、共感を示すメッセージシリーズ",
                "triggers": [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "疲れた時の励まし",
                        "enabled": True,
                        "keywords": ["疲れた", "つかれた", "だるい", "しんどい", "眠い"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} お疲れ様です！無理しないでくださいね",
                            ">>{{no}} 疲れた時は休むのが一番ですよ〜",
                            ">>{{no}} 今日も一日お疲れ様でした！ゆっくり休んでください"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 2,
                        "response_delay_seconds": 0,
                        "firing_probability": 100
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "頑張ってる人への応援",
                        "enabled": True,
                        "keywords": ["頑張る", "頑張って", "努力", "挑戦", "やってみる"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} 応援してます！頑張ってください〜",
                            ">>{{no}} その意気です！きっとうまくいきますよ♪",
                            ">>{{no}} 挑戦する姿勢、素敵です！"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 1,
                        "response_delay_seconds": 0,
                        "firing_probability": 90
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "落ち込み時の慰め",
                        "enabled": True,
                        "keywords": ["落ち込む", "悲しい", "うまくいかない", "失敗", "ダメ"],
                        "keyword_condition": "OR",
                        "response_type": "predefined",
                        "messages": [
                            ">>{{no}} そんな日もありますよ。大丈夫です",
                            ">>{{no}} 落ち込まないでください。明日はきっといい日になります",
                            ">>{{no}} 失敗は成功のもと！次に活かせますよ"
                        ],
                        "ai_response_prompt": "",
                        "max_reactions_per_stream": 1,
                        "response_delay_seconds": 0,
                        "firing_probability": 100
                    }
                ]
            }
        }

        return {
            "series": default_series,
            "last_updated": datetime.now().isoformat()
        }

    def get_all_trigger_series(self) -> dict:
        """全トリガーシリーズを取得"""
        config = self.load_trigger_series()
        return config.get("series", {})

    def save_trigger_series_item(self, series_id: str, series_data: dict):
        """個別のトリガーシリーズを保存"""
        config = self.load_trigger_series()
        config["series"][series_id] = series_data
        self.save_trigger_series(config)

    def delete_trigger_series(self, series_id: str):
        """トリガーシリーズを削除"""
        config = self.load_trigger_series()
        if series_id in config["series"]:
            del config["series"][series_id]
            self.save_trigger_series(config)

    def get_trigger_series(self, series_id: str) -> dict:
        """特定のトリガーシリーズを取得"""
        all_series = self.get_all_trigger_series()
        return all_series.get(series_id, {})

    def notify_websocket_config_reload(self, user_id: str):
        """WebSocketサーバーに設定再読み込みを通知"""
        def send_notification():
            try:
                print(f"[CONFIG] Notifying WebSocket server to reload config for user {user_id}")

                def on_message(ws, message):
                    response = json.loads(message)
                    if response.get('type') == 'config_reload_response':
                        print(f"[CONFIG] Server responded: {response.get('status', 'unknown')}")

                def on_error(ws, error):
                    print(f"[CONFIG] WebSocket error during config reload: {error}")

                def on_close(ws, close_status_code, close_msg):
                    pass

                def on_open(ws):
                    reload_message = {
                        'type': 'reload_user_config',
                        'user_id': user_id
                    }
                    ws.send(json.dumps(reload_message))
                    print(f"[CONFIG] Sent reload notification for user {user_id}")
                    # 短時間で接続を閉じる
                    threading.Timer(1.0, ws.close).start()

                ws = websocket.WebSocketApp('ws://localhost:8766',
                                          on_open=on_open,
                                          on_message=on_message,
                                          on_error=on_error,
                                          on_close=on_close)

                # 別スレッドで実行して非同期にする
                ws.run_forever()

            except Exception as e:
                print(f"[CONFIG] Failed to notify WebSocket server: {e}")

        # バックグラウンドで通知を送信
        notification_thread = threading.Thread(target=send_notification, daemon=True)
        notification_thread.start()

# 既存コードとの互換性
NCVSpecialConfigManager = HierarchicalConfigManager
IndividualConfigManager = HierarchicalConfigManager