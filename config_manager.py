import json
import os
from datetime import datetime

class NCVSpecialConfigManager:
    def __init__(self):
        self.config_dir = os.path.abspath("config")
        self.config_file = os.path.join(self.config_dir, "ncv_special_config.json")
        self.processed_xmls_file = os.path.join(self.config_dir, "processed_xmls.json")
        self.ensure_directories()
    
    def ensure_directories(self):
        """必要なディレクトリを作成"""
        os.makedirs(self.config_dir, exist_ok=True)
        
        # デフォルト設定を作成
        if not os.path.exists(self.config_file):
            self.create_default_config()
    
    def create_default_config(self):
        """デフォルト設定を作成"""
        default_config = {
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
            "special_users_config": {
                "default_analysis_enabled": True,
                "default_analysis_ai_model": "openai-gpt4o",
                "default_analysis_prompt": "以下のユーザーのコメント履歴を分析して、このユーザーの特徴、傾向、配信との関わり方について詳しく分析してください。\\n\\n分析観点：\\n- コメントの頻度と投稿タイミング\\n- コメント内容の傾向（質問、感想、ツッコミなど）\\n- 配信者との関係性\\n- 他の視聴者との関わり\\n- このユーザーの配信に対する貢献度\\n- 特徴的な発言や行動パターン",
                "default_template": "user_detail.html",
                "users": {}
            },
            "last_updated": datetime.now().isoformat()
        }
        
        self.save_config(default_config)
    
    def load_config(self):
        """設定を読み込み"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 設定の補完（後方互換性）
            default_config = self.get_default_config_template()
            merged_config = self._merge_config_deep(default_config, config)
            
            return merged_config
        except Exception as e:
            print(f"設定読み込みエラー: {str(e)}")
            return self.get_default_config_template()
    
    def save_config(self, config):
        """設定を保存"""
        config["last_updated"] = datetime.now().isoformat()
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
    
    def get_default_config_template(self):
        """デフォルト設定テンプレートを取得"""
        return {
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
            "special_users_config": {
                "default_analysis_enabled": True,
                "default_analysis_ai_model": "openai-gpt4o",
                "default_analysis_prompt": "以下のユーザーのコメント履歴を分析してください...",
                "default_template": "user_detail.html",
                "users": {}
            }
        }
    
    def _merge_config_deep(self, default, loaded):
        """設定を深くマージして不足項目を補完"""
        result = default.copy()
        
        for key, value in loaded.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = self._merge_config_deep(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    def get_special_users_list(self):
        """スペシャルユーザーIDのリストを取得"""
        config = self.load_config()
        special_users_config = config.get("special_users_config", {})
        users = special_users_config.get("users", {})
        return list(users.keys())
    
    def get_user_config(self, user_id):
        """個別ユーザーの設定を取得"""
        config = self.load_config()
        special_users_config = config.get("special_users_config", {})
        users = special_users_config.get("users", {})
        
        if user_id in users:
            return users[user_id]
        
        # デフォルト設定を返す
        return {
            "user_id": user_id,
            "display_name": f"ユーザー{user_id}",
            "analysis_enabled": special_users_config.get("default_analysis_enabled", True),
            "analysis_ai_model": special_users_config.get("default_analysis_ai_model", "openai-gpt4o"),
            "analysis_prompt": special_users_config.get("default_analysis_prompt", ""),
            "template": special_users_config.get("default_template", "user_detail.html"),
            "description": "",
            "tags": []
        }
    
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