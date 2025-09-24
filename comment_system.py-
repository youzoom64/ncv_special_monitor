#!/usr/bin/env python3
"""
ニコ生184自動返信システム（完成版）
- ポート8766固定
- 特別ユーザーコメント検知時に SpecialUser/.../list.html のハッシュ比較
- ハッシュが変わっていたら EXE起動＋10秒後にコメント送信
- send_message のテンプレート置換対応（{no} {display_name} {user_id} {live_title}）
- ハッシュは config/ncv_special_config.json に保存
- 放送終了検知あり
"""

import asyncio
import websockets
import json
import time
import threading
import sys
import os
import re
import subprocess
import hashlib
import requests

CONFIG_PATH = "config/ncv_special_config.json"

class SpecialUserHashManager:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = config_path
        self.config_data = {}
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config_data = json.load(f)
        else:
            self.config_data = {"special_users_config": {"users": {}}}

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, ensure_ascii=False, indent=2)

    def get_user_entry(self, user_id):
        return (
            self.config_data
            .get("special_users_config", {})
            .get("users", {})
            .get(str(user_id), {})
        )

    def get_last_hash(self, user_id):
        return self.get_user_entry(user_id).get("last_hash")

    def set_last_hash(self, user_id, new_hash):
        users = self.config_data.setdefault("special_users_config", {}).setdefault("users", {})
        user_entry = users.setdefault(str(user_id), {})
        user_entry["last_hash"] = new_hash
        self.save_config()

def compute_list_html_hash(user_id, display_name):
    folder = f"SpecialUser/{user_id}_{display_name}"
    list_path = os.path.join(folder, "list.html")
    if not os.path.exists(list_path):
        return None, list_path
    with open(list_path, "rb") as f:
        content = f.read()
    return hashlib.md5(content).hexdigest(), list_path

def format_message(template, *, no, display_name, user_id, live_title=None):
    try:
        return template.format(
            no=no,
            display_name=display_name,
            user_id=user_id,
            live_title=live_title or ""
        )
    except Exception as e:
        print(f"⚠️ テンプレート置換失敗: {e}")
        return template

class CommentTransceiver:
    def __init__(self, broadcast_url=None):
        self.uri = "ws://localhost:8766"
        self.websocket = None
        self.connected = False
        self.special_users = {}
        self.broadcast_url = broadcast_url
        self.broadcast_id = None
        self.hash_manager = SpecialUserHashManager()
        
        if broadcast_url:
            self.broadcast_id = self.extract_broadcast_id(broadcast_url)
        self.load_special_users_config()
        
    def extract_broadcast_id(self, url):
        patterns = [
            r'https?://live\.nicovideo\.jp/watch/(lv\d+)',
            r'https?://live2\.nicovideo\.jp/watch/(lv\d+)',
            r'https?://nico\.ms/(lv\d+)',
            r'^(lv\d+)$'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
        
    def load_special_users_config(self):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.special_users = config.get("special_users_config", {}).get("users", {})
            print(f"🔧 特別ユーザー設定読み込み: {len(self.special_users)}人")
        except FileNotFoundError:
            print(f"⚠️ 設定ファイルが見つかりません: {CONFIG_PATH}")
            self.special_users = {}
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析エラー: {e}")
            self.special_users = {}
    
    def get_special_user_config(self, user_id: str):
        return self.special_users.get(str(user_id))
    
    async def connect_and_run(self):
        print("🔌 WebSocket接続中...")
        print(f"接続先: {self.uri}")
        if self.broadcast_id:
            print(f"📺 放送ID: {self.broadcast_id}")
        print("=" * 60)
        
        try:
            async with websockets.connect(self.uri) as websocket:
                self.websocket = websocket
                self.connected = True
                print("✅ 接続完了 - 特別ユーザー監視開始")
                if self.broadcast_id:
                    threading.Thread(target=self._end_detection_loop, daemon=True).start()
                
                input_thread = threading.Thread(target=self.input_worker, daemon=True)
                input_thread.start()
                
                async for message in websocket:
                    await self.handle_received_message(message)
                    
        except websockets.exceptions.ConnectionRefused:
            print("❌ 接続失敗: WebSocketサーバーが起動していません (localhost:8766)")
        except Exception as e:
            print(f"❌ エラー: {e}")
        finally:
            self.connected = False
    
    async def handle_received_message(self, message: str):
        try:
            data = json.loads(message)
            comment = data.get("comment", "")
            user_id = data.get("user_id", "不明")
            comment_no = data.get("comment_no", "")
            broadcast_id = data.get("broadcast_id", "")

            if self.broadcast_id and broadcast_id and broadcast_id != self.broadcast_id:
                return

            special_config = self.get_special_user_config(user_id)
            if special_config:
                display_name = special_config.get("display_name", "")
                template = special_config.get("send_message", "")
                current_hash, path = compute_list_html_hash(user_id, display_name)
                if not current_hash:
                    print(f"⚠️ list.html が存在しません: {path}")
                    return
                last_hash = self.hash_manager.get_last_hash(user_id)
                if current_hash != last_hash:
                    formatted_msg = format_message(
                        template,
                        no=comment_no,
                        display_name=display_name,
                        user_id=user_id,
                        live_title=self.broadcast_id
                    )
                    print(f"⭐ {display_name} の list.html 更新検知 → コメント送信")
                    self.hash_manager.set_last_hash(user_id, current_hash)
                    self._launch_and_send(formatted_msg)
                else:
                    print(f"⏭️ {display_name} の list.html 変更なし → 無視")

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"❌ メッセージ処理エラー: {e}")
    
    def _launch_and_send(self, message):
        try:
            exe_path = r"C:\Users\youzo\OneDrive\デスクトップ 1\send_ncv\NiconamaCommentViewer.exe"
            subprocess.Popen([exe_path, self.broadcast_id], shell=True)
            print(f"🚀 NiconamaCommentViewer起動: {self.broadcast_id}")
        except Exception as e:
            print(f"❌ NiconamaCommentViewer起動エラー: {e}")
        
        def delayed_send():
            try:
                asyncio.run_coroutine_threadsafe(
                    self.send_anonymous_comment(message),
                    asyncio.get_event_loop()
                )
                print(f"📤 10秒後にコメント送信: {message}")
            except Exception as e:
                print(f"❌ 遅延送信エラー: {e}")

        threading.Timer(10.0, delayed_send).start()

    def input_worker(self):
        while self.connected:
            try:
                user_input = input()
                if user_input.lower() in ['exit', 'quit']:
                    print("👋 終了します...")
                    if self.websocket:
                        asyncio.run_coroutine_threadsafe(
                            self.websocket.close(), asyncio.get_event_loop()
                        )
                    break
            except EOFError:
                break
            except Exception as e:
                print(f"❌ 入力エラー: {e}")

    async def send_anonymous_comment(self, message: str):
        try:
            if not self.websocket or self.websocket.closed:
                print("❌ WebSocket接続がありません")
                return
            send_data = {
                "action": "send_comment",
                "message": message,
                "anonymous": True,
                "broadcast_id": self.broadcast_id,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            await self.websocket.send(json.dumps(send_data, ensure_ascii=False))
        except Exception as e:
            print(f"❌ 送信エラー: {e}")

    def _end_detection_loop(self):
        """放送終了検知ループ"""
        while self.connected:
            try:
                if self._check_broadcast_end():
                    print(f"📺 放送終了検知: {self.broadcast_id}")
                    if self.websocket:
                        asyncio.run_coroutine_threadsafe(
                            self.websocket.close(), asyncio.get_event_loop()
                        )
                    time.sleep(1)
                    print("👋 放送終了のため自動終了します")
                    os._exit(0)
            except Exception as e:
                print(f"⚠️ 終了検知エラー: {e}")
            time.sleep(30)

    def _check_broadcast_end(self):
        try:
            url = f"https://live.nicovideo.jp/watch/{self.broadcast_id}"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            html = r.text
            end_patterns = [
                'data-status="endPublication"', '公開終了',
                'data-status="ended"', '放送は終了',
                '番組は終了', '配信終了', '視聴できません'
            ]
            return any(p in html for p in end_patterns)
        except Exception:
            return False

def main():
    broadcast_url = sys.argv[1] if len(sys.argv) > 1 else None
    transceiver = CommentTransceiver(broadcast_url)
    try:
        asyncio.run(transceiver.connect_and_run())
    except KeyboardInterrupt:
        print("\n👋 終了します")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")

if __name__ == "__main__":
    main()
