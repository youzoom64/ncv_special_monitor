import os
import json
import shutil
from pathlib import Path

class ConfigMigrator:
    def __init__(self):
        self.old_config_path = "config/ncv_special_config.json"
        self.specialuser_root = Path("SpecialUser")
        
    def migrate_to_individual_configs(self):
        """中央設定を個別設定に分割"""
        
        # 元の設定を読み込み
        with open(self.old_config_path, 'r', encoding='utf-8') as f:
            old_config = json.load(f)
        
        users_config = old_config.get("special_users_config", {}).get("users", {})
        global_settings = {
            "api_settings": old_config.get("api_settings", {}),
            "default_analysis_ai_model": old_config.get("special_users_config", {}).get("default_analysis_ai_model", "openai-gpt4o"),
            "default_analysis_prompt": old_config.get("special_users_config", {}).get("default_analysis_prompt", "")
        }
        
        print(f"移行対象ユーザー: {len(users_config)}人")
        
        # 各ユーザーディレクトリに個別config.jsonを作成
        for user_id, user_config in users_config.items():
            display_name = user_config.get("display_name", f"ユーザー{user_id}")
            user_dir = self.specialuser_root / f"{user_id}_{display_name}"
            
            # ディレクトリ作成
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # 個別設定作成
            individual_config = {
                "user_info": {
                    "user_id": user_id,
                    "display_name": display_name,
                    "description": user_config.get("description", ""),
                    "tags": user_config.get("tags", [])
                },
                "ai_analysis": {
                    "enabled": user_config.get("analysis_enabled", True),
                    "model": user_config.get("analysis_ai_model", global_settings["default_analysis_ai_model"]),
                    "custom_prompt": user_config.get("analysis_prompt", ""),
                    "use_default_prompt": not bool(user_config.get("analysis_prompt", "").strip())
                },
                "comment_system": {
                    "send_message": user_config.get("send_message", ""),
                    "trigger_conditions": user_config.get("trigger_conditions", {
                        "enabled": True,
                        "trigger_type": "first_comment",
                        "keywords": [],
                        "max_reactions_per_stream": 1,
                        "cooldown_minutes": 30
                    })
                },
                "template_settings": {
                    "template": user_config.get("template", "user_detail.html")
                },
                "metadata": {
                    "created_at": "2025-09-24T00:00:00",
                    "migrated_from_central_config": True,
                    "config_version": "2.0"
                }
            }
            
            # 個別config.json保存
            config_path = user_dir / "config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(individual_config, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 移行完了: {user_id} ({display_name})")
        
        # グローバル設定を別途保存（API設定など）
        global_config_path = self.specialuser_root / "global_config.json"
        with open(global_config_path, 'w', encoding='utf-8') as f:
            json.dump(global_settings, f, ensure_ascii=False, indent=2)
        
        # 元設定ファイルをバックアップ
        backup_path = f"{self.old_config_path}.backup_{int(time.time())}"
        shutil.copy2(self.old_config_path, backup_path)
        
        print(f"✅ 移行完了: {len(users_config)}ユーザーの個別設定を作成")
        print(f"📁 グローバル設定: {global_config_path}")
        print(f"💾 バックアップ: {backup_path}")

if __name__ == "__main__":
    migrator = ConfigMigrator()
    migrator.migrate_to_individual_configs()