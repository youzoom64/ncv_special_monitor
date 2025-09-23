# config_manager.py (完全書き換え)
import json
import os
from pathlib import Path
from datetime import datetime
import shutil

class IndividualConfigManager:
    def __init__(self):
        self.specialuser_root = Path("SpecialUser")
        self.global_config_path = self.specialuser_root / "global_config.json"
        self.processed_xmls_file = Path("config") / "processed_xmls.json"
        
        # SpecialUserディレクトリ作成
        self.specialuser_root.mkdir(exist_ok=True)
    
    def load_config(self):
        """既存のload_config互換のため、グローバル設定を返す（special_users_configも含む）"""
        global_config = self.load_global_config()

        # special_users_configセクションを追加
        all_users = self.get_all_special_users()
        special_users_config = {
            "users": {},
            "default_analysis_prompt": global_config.get("default_analysis_prompt", "以下のユーザーのコメント履歴を分析してください...")
        }

        # 全スペシャルユーザーを special_users_config 形式に変換
        for user in all_users:
            user_id = user["user_id"]
            special_users_config["users"][user_id] = {
                "user_id": user_id,
                "display_name": user["display_name"],
                "analysis_enabled": user["analysis_enabled"],
                "analysis_ai_model": user["analysis_ai_model"],
                "analysis_prompt": user["analysis_prompt"],
                "template": user["template"],
                "description": user["description"],
                "tags": user["tags"]
            }

        global_config["special_users_config"] = special_users_config
        return global_config
    
    def load_global_config(self) -> dict:
        """グローバル設定（API設定など）を読み込み"""
        if self.global_config_path.exists():
            with open(self.global_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # デフォルトグローバル設定
        default_global = {
            "ncv_folder_path": "C:\\Users\\youzo\\AppData\\Roaming\\posite-c\\NiconamaCommentViewer\\CommentLog",
            "monitor_enabled": True,
            "check_interval_minutes": 5,
            "retry_count": 3,
            "api_settings": {
                "summary_ai_model": "openai-gpt4o",
                "openai_api_key": "",
                "google_api_key": "",
                "suno_api_key": "",
                "imgur_api_key": ""
            },
            "default_analysis_ai_model": "openai-gpt4o",
            "default_analysis_prompt": "以下のユーザーのコメント履歴を分析してください...",
            "last_updated": datetime.now().isoformat()
        }
        
        self.save_global_config(default_global)
        return default_global
    
    def save_config(self, config: dict):
        """設定を保存（グローバル設定とユーザー設定の両方）"""
        # special_users_configがある場合は、それを個別ユーザー設定として保存
        if "special_users_config" in config:
            special_users = config["special_users_config"].get("users", {})
            for user_id, user_config in special_users.items():
                self.save_user_config(
                    user_id=user_id,
                    display_name=user_config.get("display_name", f"ユーザー{user_id}"),
                    config=self.convert_to_full_user_config(user_config)
                )
            # special_users_configはグローバル設定から除外
            del config["special_users_config"]

        # グローバル設定を保存
        self.save_global_config(config)

    def save_global_config(self, config: dict):
        """グローバル設定を保存"""
        config["last_updated"] = datetime.now().isoformat()
        with open(self.global_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def convert_to_full_user_config(self, user_config: dict) -> dict:
        """GUI形式のユーザー設定を完全な個別ユーザー設定に変換"""
        return {
            "user_info": {
                "user_id": user_config.get("user_id", ""),
                "display_name": user_config.get("display_name", ""),
                "description": user_config.get("description", ""),
                "tags": user_config.get("tags", [])
            },
            "ai_analysis": {
                "enabled": user_config.get("analysis_enabled", True),
                "model": user_config.get("analysis_ai_model", "openai-gpt4o"),
                "custom_prompt": user_config.get("analysis_prompt", ""),
                "use_default_prompt": not bool(user_config.get("analysis_prompt", "").strip())
            },
            "comment_system": {
                "enabled": user_config.get("comment_system_enabled", True),
                "send_messages": user_config.get("send_messages", [f">>{'{no}'} こんにちは、{user_config.get('display_name', '')}さん"]),
                "trigger_conditions": {
                    "enabled": user_config.get("trigger_enabled", True),
                    "trigger_type": user_config.get("trigger_type", "first_comment"),
                    "keywords": user_config.get("keywords", ["こんにちは", "初見"]),
                    "max_reactions_per_stream": user_config.get("max_reactions_per_stream", 1),
                    "cooldown_minutes": user_config.get("cooldown_minutes", 30)
                },
                "owner_id_overrides": user_config.get("owner_id_overrides", {})
            },
            "template_settings": {
                "template": user_config.get("template", "user_detail.html")
            },
            "metadata": {
                "created_at": user_config.get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
                "config_version": "3.0"
            }
        }
    
    def load_user_config(self, user_id: str, display_name: str = None) -> dict:

        """個別ユーザー設定を読み込み"""
        if display_name is None:
            # SpecialUserディレクトリ内を検索してuser_idが一致するものを探す
            for user_dir in self.specialuser_root.iterdir():
                if user_dir.is_dir() and user_dir.name.startswith(f"{user_id}_"):
                    config_path = user_dir / "config.json"
                    if config_path.exists():
                        with open(config_path, 'r', encoding='utf-8') as f:
                            return json.load(f)
            
            # 見つからなければ fallback
            display_name = f"ユーザー{user_id}"
        
        # 通常のパスで読み込み
        user_dir = self.specialuser_root / f"{user_id}_{display_name}"
        config_path = user_dir / "config.json"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # ✨ 編集画面に対応した形式に変換 ✨
            comment_system = data.get("comment_system", {})
            trigger_conditions = comment_system.get("trigger_conditions", {})

            return {
                "user_id": data["user_info"]["user_id"],
                "display_name": data["user_info"]["display_name"],
                "analysis_enabled": data["ai_analysis"].get("enabled", True),
                "analysis_ai_model": data["ai_analysis"].get("model", "openai-gpt4o"),
                "analysis_prompt": data["ai_analysis"].get("custom_prompt", ""),
                "template": data.get("template_settings", {}).get("template", "user_detail.html"),
                "description": data["user_info"].get("description", ""),
                "tags": data["user_info"].get("tags", []),
                # コメントシステム設定
                "comment_system_enabled": comment_system.get("enabled", True),
                "send_messages": comment_system.get("send_messages", []),
                "trigger_enabled": trigger_conditions.get("enabled", True),
                "trigger_type": trigger_conditions.get("trigger_type", "first_comment"),
                "keywords": trigger_conditions.get("keywords", []),
                "max_reactions_per_stream": trigger_conditions.get("max_reactions_per_stream", 1),
                "cooldown_minutes": trigger_conditions.get("cooldown_minutes", 30),
                "owner_id_overrides": comment_system.get("owner_id_overrides", {})
            }

        return self.create_default_user_config(user_id, display_name)

    
    def create_default_user_config(self, user_id: str, display_name: str) -> dict:
        """デフォルトの個別ユーザー設定を作成"""
        return {
            "user_info": {
                "user_id": user_id,
                "display_name": display_name,
                "description": "",
                "tags": []
            },
            "ai_analysis": {
                "enabled": True,
                "model": "openai-gpt4o",
                "custom_prompt": "",
                "use_default_prompt": True
            },
            "comment_system": {
                "enabled": True,
                "send_messages": [
                    f">>{'{no}'} こんにちは、{display_name}さん"
                ],
                "trigger_conditions": {
                    "enabled": True,
                    "trigger_type": "first_comment",
                    "keywords": ["こんにちは", "初見"],
                    "max_reactions_per_stream": 1,
                    "cooldown_minutes": 30
                },
                "owner_id_overrides": {}
            },
            "template_settings": {
                "template": "user_detail.html"
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "config_version": "3.0"
            }
        }
    
    def save_user_config(self, user_id: str, display_name: str, config: dict):
        """個別ユーザー設定を保存"""
        user_dir = self.specialuser_root / f"{user_id}_{display_name}"
        user_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = user_dir / "config.json"
        config["metadata"]["updated_at"] = datetime.now().isoformat()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def get_all_special_users(self) -> list:
        """全スペシャルユーザーのリストを取得（編集画面用に展開）"""
        users = []
        for user_dir in self.specialuser_root.iterdir():
            if user_dir.is_dir() and "_" in user_dir.name and not user_dir.name.startswith("global"):
                config_path = user_dir / "config.json"
                if config_path.exists():
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        comment_system = data.get("comment_system", {})
                        trigger_conditions = comment_system.get("trigger_conditions", {})

                        users.append({
                            "user_id": data["user_info"]["user_id"],
                            "display_name": data["user_info"]["display_name"],
                            "analysis_enabled": data["ai_analysis"].get("enabled", True),
                            "analysis_ai_model": data["ai_analysis"].get("model", ""),
                            "analysis_prompt": data["ai_analysis"].get("custom_prompt", ""),
                            "template": data.get("template_settings", {}).get("template", ""),
                            "description": data["user_info"].get("description", ""),
                            "tags": data["user_info"].get("tags", []),
                            # コメントシステム設定
                            "comment_system_enabled": comment_system.get("enabled", True),
                            "send_messages": comment_system.get("send_messages", []),
                            "trigger_enabled": trigger_conditions.get("enabled", True),
                            "trigger_type": trigger_conditions.get("trigger_type", "first_comment"),
                            "keywords": trigger_conditions.get("keywords", []),
                            "max_reactions_per_stream": trigger_conditions.get("max_reactions_per_stream", 1),
                            "cooldown_minutes": trigger_conditions.get("cooldown_minutes", 30),
                            "owner_id_overrides": comment_system.get("owner_id_overrides", {})
                        })
                    except Exception as e:
                        print(f"設定読み込みエラー {user_dir.name}: {e}")
        return users

    
    def get_special_users_list(self):
        """既存のget_special_users_list互換"""
        users = self.get_all_special_users()
        return [user["user_id"] for user in users]
    
    def get_user_config(self, user_id):
        """既存のget_user_config互換"""
        users = self.get_all_special_users()
        for user in users:
            if user["user_id"] == user_id:
                return self.load_user_config(user_id, user["display_name"])
        
        # 見つからない場合はデフォルトを返す
        return self.create_default_user_config(user_id, f"ユーザー{user_id}")
    
    # 既存の処理済みXML管理メソッドはそのまま維持
    def load_processed_xmls(self):
        """処理済みXMLリストを読み込み"""
        try:
            if os.path.exists(self.processed_xmls_file):
                with open(self.processed_xmls_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get("processed_xmls", [])
        except Exception as e:
            print(f"処理済みXML読み込みエラー: {str(e)}")
        return []
    
    def save_processed_xmls(self, processed_list):
        """処理済みXMLリストを保存"""
        try:
            os.makedirs(os.path.dirname(self.processed_xmls_file), exist_ok=True)
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

# 既存のコードとの互換性のため
NCVSpecialConfigManager = IndividualConfigManager