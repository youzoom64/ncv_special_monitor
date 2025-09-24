# config_manager_v4.py - 新しい階層構造対応
import json
import os
from pathlib import Path
from datetime import datetime
import uuid

class HierarchicalConfigManager:
    def __init__(self):
        self.config_root = Path("config")
        self.global_config_path = self.config_root / "global_config.json"
        self.processed_xmls_file = self.config_root / "processed_xmls.json"

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

    def save_global_config(self, config: dict):
        """グローバル設定を保存"""
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
        """全スペシャルユーザーを取得"""
        config = self.load_global_config()
        return config.get("special_users_config", {}).get("users", {})

    def get_user_config(self, user_id: str) -> dict:
        """特定のユーザー設定を取得"""
        users = self.get_all_special_users()
        return users.get(user_id, self.create_default_user_config(user_id))

    def save_user_config(self, user_id: str, user_config: dict):
        """ユーザー設定を保存"""
        config = self.load_global_config()
        if "special_users_config" not in config:
            config["special_users_config"] = {"users": {}}

        user_config["metadata"] = {
            "created_at": user_config.get("metadata", {}).get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "config_version": "4.0"
        }

        config["special_users_config"]["users"][user_id] = user_config
        self.save_global_config(config)

    def delete_user_config(self, user_id: str):
        """ユーザー設定を削除"""
        config = self.load_global_config()
        users = config.get("special_users_config", {}).get("users", {})
        if user_id in users:
            del users[user_id]
            self.save_global_config(config)

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
        default_messages = default_response.get("messages", [f">>{'{no}'} こんにちは、{display_name}さん"])
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
        user_config = self.get_user_config(user_id)
        if "broadcasters" not in user_config:
            user_config["broadcasters"] = {}

        user_config["broadcasters"][broadcaster_id] = broadcaster_config
        self.save_user_config(user_id, user_config)

    def delete_broadcaster_config(self, user_id: str, broadcaster_id: str):
        """配信者設定を削除"""
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
        user_config = self.get_user_config(user_id)

        if "broadcasters" not in user_config:
            user_config["broadcasters"] = {}
        if broadcaster_id not in user_config["broadcasters"]:
            user_config["broadcasters"][broadcaster_id] = self.create_default_broadcaster_config(broadcaster_id)

        triggers = user_config["broadcasters"][broadcaster_id].get("triggers", [])

        # IDが存在しない場合は生成
        if "id" not in trigger_config:
            trigger_config["id"] = str(uuid.uuid4())

        # 既存トリガーを更新、なければ追加
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

    def delete_trigger_config(self, user_id: str, broadcaster_id: str, trigger_id: str):
        """トリガー設定を削除"""
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
        """スペシャルトリガー設定を保存"""
        user_config = self.get_user_config(user_id)
        special_triggers = user_config.get("special_triggers", [])

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

        user_config["special_triggers"] = special_triggers
        self.save_user_config(user_id, user_config)

    def delete_special_trigger_config(self, user_id: str, trigger_id: str):
        """スペシャルトリガー設定を削除"""
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

# 既存コードとの互換性
NCVSpecialConfigManager = HierarchicalConfigManager
IndividualConfigManager = HierarchicalConfigManager