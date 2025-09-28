"""
step00_profile_monitor.py

パイプライン用プロフィールモニタリングプロセッサ
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Seleniumのログを無効化
logging.getLogger('selenium').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)


class UserProfileMonitor:
    def __init__(self, user_id: str, user_name: str, base_dir: str = "SpecialUser"):
        self.user_id = user_id
        self.user_name = user_name
        self.base_dir = base_dir
        self.user_dir = os.path.join(base_dir, f"{user_id}_{user_name}")
        self.profile_dir = os.path.join(self.user_dir, "profile")
        self.config_path = os.path.join(self.user_dir, "config.json")

        # ディレクトリを作成
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.user_dir, exist_ok=True)
        os.makedirs(self.profile_dir, exist_ok=True)

    def get_user_page_html(self, url: str) -> Optional[str]:
        """ユーザーページのHTMLを取得（Seleniumでレンダリング後）"""
        driver = None
        try:
            import time

            # Seleniumでページを開く
            driver = self.setup_webdriver()
            driver.get(url)

            # ページが完全に読み込まれるまで待機
            time.sleep(5)

            # UserDetailsContainerが読み込まれるまで待機
            try:
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "UserDetailsContainer")))
            except:
                time.sleep(3)

            # 完全にレンダリングされたHTMLを取得
            html_content = driver.page_source
            return html_content

        except Exception as e:
            return None
        finally:
            if driver:
                driver.quit()

    def setup_webdriver(self) -> webdriver.Chrome:
        """Chromeドライバーの設定"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-javascript')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--silent')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})

        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def take_element_screenshot(self, url: str, element_class: str = "UserDetailsContainer") -> Optional[str]:
        """指定されたdiv要素のスクリーンショットを撮影"""
        driver = None
        try:
            driver = self.setup_webdriver()
            driver.get(url)

            # 要素が読み込まれるまで待機
            wait = WebDriverWait(driver, 10)
            element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, element_class)))

            # スクリーンショットファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"profile_{timestamp}.png"
            screenshot_path = os.path.join(self.profile_dir, screenshot_filename)

            # 要素のスクリーンショットを撮影
            element.screenshot(screenshot_path)
            return screenshot_path

        except Exception as e:
            return None
        finally:
            if driver:
                driver.quit()

    def calculate_element_hash(self, html_content: str, element_class: str = "UserDetailsContainer") -> Optional[str]:
        """HTML要素のハッシュ値を計算"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            target_div = soup.find('div', class_=element_class)

            if not target_div:
                return None

            # 要素の内容をテキストとして取得してハッシュ化
            element_text = str(target_div).encode('utf-8')
            hash_value = hashlib.sha256(element_text).hexdigest()
            return hash_value

        except Exception as e:
            return None

    def extract_user_description(self, html_content: str) -> Optional[str]:
        """ユーザー説明文を抽出"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            description_div = soup.find('div', class_='ExpandBox-collapsed')

            if description_div:
                return description_div.get_text(strip=True)
            return None

        except Exception as e:
            return None

    def load_config(self) -> Dict[str, Any]:
        """config.jsonを読み込み"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 新しい設定ファイルのテンプレート
                return {
                    "user_info": {
                        "user_id": self.user_id,
                        "display_name": self.user_name,
                        "enabled": True,
                        "description": "",
                        "tags": []
                    },
                    "profile_monitoring": {
                        "last_hash": "",
                        "last_screenshot": "",
                        "last_check": "",
                        "user_description": ""
                    },
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "config_version": "5.0"
                    }
                }
        except Exception as e:
            return {}

    def save_config(self, config: Dict[str, Any]) -> bool:
        """config.jsonを保存"""
        try:
            config["metadata"]["updated_at"] = datetime.now().isoformat()

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True

        except Exception as e:
            return False

    def check_profile_changes(self, url: str) -> Dict[str, Any]:
        """プロフィール変更をチェック"""
        result = {
            "changed": False,
            "screenshot_path": None,
            "hash_value": None,
            "previous_hash": None,
            "user_description": None,
            "error": None
        }

        try:
            # HTMLを取得
            html_content = self.get_user_page_html(url)
            if not html_content:
                result["error"] = "HTMLの取得に失敗"
                return result

            # ハッシュ値を計算
            current_hash = self.calculate_element_hash(html_content)
            if not current_hash:
                result["error"] = "ハッシュ値の計算に失敗"
                return result

            # ユーザー説明文を抽出
            user_description = self.extract_user_description(html_content)

            # 設定ファイルを読み込み
            config = self.load_config()
            previous_hash = config.get("profile_monitoring", {}).get("last_hash", "")

            result["hash_value"] = current_hash
            result["previous_hash"] = previous_hash
            result["user_description"] = user_description

            # 初回実行または変更されているかチェック
            is_first_time = previous_hash == ""
            if is_first_time or current_hash != previous_hash:
                result["changed"] = True

                # スクリーンショットを撮影
                screenshot_path = self.take_element_screenshot(url)
                if screenshot_path:
                    result["screenshot_path"] = screenshot_path

                    # 設定ファイルを更新
                    if "profile_monitoring" not in config:
                        config["profile_monitoring"] = {}

                    config["profile_monitoring"]["last_hash"] = current_hash
                    config["profile_monitoring"]["last_screenshot"] = screenshot_path
                    config["profile_monitoring"]["last_check"] = datetime.now().isoformat()
                    config["profile_monitoring"]["user_description"] = user_description or ""

                    # user_infoのdescriptionも更新
                    if "user_info" not in config:
                        config["user_info"] = {}
                    config["user_info"]["description"] = user_description or ""

                    self.save_config(config)
                else:
                    result["error"] = "スクリーンショットの撮影に失敗"
            else:
                # 最終チェック時刻だけ更新
                if "profile_monitoring" not in config:
                    config["profile_monitoring"] = {}
                config["profile_monitoring"]["last_check"] = datetime.now().isoformat()
                config["profile_monitoring"]["user_description"] = user_description or ""

                # user_infoのdescriptionも更新（変更がなくても最新の説明文で更新）
                if "user_info" not in config:
                    config["user_info"] = {}
                config["user_info"]["description"] = user_description or ""

                self.save_config(config)

        except Exception as e:
            result["error"] = f"処理中にエラーが発生: {e}"

        return result


def process(pipeline_data):
    """プロフィールモニタリング処理"""
    try:
        # 設定からユーザー情報を取得
        config = pipeline_data.get('config', {})
        user_info = config.get('user_info', {})
        lv_value = pipeline_data.get('lv_value')
        subfolder_name = pipeline_data.get('subfolder_name')

        user_id = user_info.get('user_id')
        user_name = user_info.get('display_name')

        if not user_id or not user_name:
            return {
                'success': False,
                'error': 'ユーザー情報が不足しています',
                'profile_changed': False
            }

        # プロフィール監視を実行
        url = f"https://www.nicovideo.jp/user/{user_id}"
        monitor = UserProfileMonitor(user_id, user_name)
        result = monitor.check_profile_changes(url)

        # lv_id別data.jsonに説明文を保存
        if result.get('user_description') and lv_value:
            save_user_description_to_data_json(user_id, user_name, lv_value, result.get('user_description'))

        return {
            'success': not bool(result.get('error')),
            'error': result.get('error'),
            'profile_changed': result.get('changed', False),
            'hash_value': result.get('hash_value'),
            'previous_hash': result.get('previous_hash'),
            'screenshot_path': result.get('screenshot_path'),
            'user_description': result.get('user_description'),
            'user_id': user_id,
            'user_name': user_name,
            'lv_value': lv_value
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'プロフィール監視エラー: {str(e)}',
            'profile_changed': False
        }


def save_user_description_to_data_json(user_id: str, user_name: str, lv_value: str, user_description: str):
    """lv_id別のdata.jsonにユーザー説明文を保存"""
    try:
        # data.jsonのパスを構築
        user_dir = os.path.join("SpecialUser", f"{user_id}_{user_name}")
        lv_dir = os.path.join(user_dir, lv_value)
        data_json_path = os.path.join(lv_dir, "data.json")

        # ディレクトリが存在しない場合は作成
        os.makedirs(lv_dir, exist_ok=True)

        # 既存のdata.jsonを読み込み（存在しない場合は空の辞書）
        data = {}
        if os.path.exists(data_json_path):
            with open(data_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # ユーザー説明文を追加
        if 'user_profile' not in data:
            data['user_profile'] = {}

        data['user_profile']['description'] = user_description
        data['user_profile']['last_updated'] = datetime.now().isoformat()

        # data.jsonに保存
        with open(data_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"data.json保存エラー: {e}")