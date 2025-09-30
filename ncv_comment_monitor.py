import asyncio
import json
import logging
import websockets
from typing import Optional, Dict, List
import sys
import os
import random
import time
from pathlib import Path
import requests
import re
import subprocess

# config_manager を import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config_manager import HierarchicalConfigManager
from gui.utils import log_to_gui

class NCVCommentServer:
    def __init__(self):
        print("[DEBUG] NCVCommentServer.__init__() 開始")
        self.clients = {}  # instance_id をキーにしたクライアント辞書

        # ログ設定を確実に適用
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            # ハンドラーが設定されていない場合は手動で設定
            os.makedirs('logs', exist_ok=True)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            # ファイルハンドラー
            file_handler = logging.FileHandler('logs/ncv_ws_server.log', encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

            # コンソールハンドラー
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(console_handler)

            self.logger.setLevel(logging.DEBUG)

        self.logger.info("[SERVER] NCVCommentServer initialized")
        print("[DEBUG] HierarchicalConfigManager初期化")
        self.config_manager = HierarchicalConfigManager()
        self.special_users_cache = {}  # user_id をキーにした特別ユーザー設定のキャッシュ
        self.monitored_user_ids = set()  # 監視対象のユーザーID集合

        print("[DEBUG] 特別ユーザー設定初回読み込み開始")
        # 初回設定読み込み
        self.load_special_users_config()

    def debug_print(self, message):
        """デバッグメッセージをターミナルに出力"""
        print(f"[DEBUG] {message}")
        self.logger.debug(message)
        
    async def handler(self, websocket, *args):
        """
        WebSocket接続ハンドラー
        websockets v10以前: handler(websocket, path)
        websockets v11以降: handler(websocket)
        """
        # pathは使用しないが、互換性のため受け取る
        path = args[0] if args else None
        
        client_info = {
            'websocket': websocket,
            'address': websocket.remote_address,
            'path': path
        }
        
        temp_id = f"temp_{len(self.clients)}_{int(time.time())}"

        try:
            # 一時的なクライアント情報を作成
            client_info.update({
                'instance_id': None,
                'live_id': None,
                'live_title': None,
                'source': 'unknown',
                'connected_at': time.time(),
                'is_ncv_plugin': False
            })

            self.clients[temp_id] = client_info
            self.logger.info(f"Client connected from {client_info['address']}")
            
            # 接続確認メッセージを送信
            await websocket.send(json.dumps({
                'type': 'connection',
                'status': 'connected',
                'message': 'Connected to NCV Comment Server'
            }))
            
            # メッセージ受信ループ
            async for message in websocket:
                client_id = await self.process_message(websocket, message, temp_id)
                if client_id and client_id != temp_id:
                    temp_id = client_id  # IDが更新された場合
                
        except websockets.exceptions.ConnectionClosedOK:
            self.logger.info(f"Client disconnected normally: {client_info['address']}")
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.warning(f"Client disconnected with error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in handler: {e}", exc_info=True)
        finally:
            # クライアント削除
            if temp_id in self.clients:
                del self.clients[temp_id]
            self.logger.info(f"Client removed from pool: {client_info['address']}")

    async def process_message(self, websocket, message: str, current_client_id: str):
        """受信メッセージの処理"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            self.logger.debug(f"Received message type: {msg_type}")

            if msg_type == 'hello':
                return await self.handle_hello(websocket, data, current_client_id)
            elif msg_type == 'ncv_comment':
                await self.handle_comment(websocket, data)
            elif msg_type == 'list_clients_request':
                await self.handle_list_clients_request(websocket)
            elif msg_type == 'send_comment_to_specific_client':
                await self.handle_send_comment_to_specific_client(websocket, data)
            elif msg_type == 'send_comment_result':
                await self.handle_send_comment_result(websocket, data, current_client_id)
            elif msg_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
            elif msg_type == 'reload_user_config':
                await self.handle_reload_user_config(websocket, data)
            else:
                self.logger.warning(f"Unknown message type: {msg_type}")

            return current_client_id
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON received: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)

        return current_client_id

    async def handle_hello(self, websocket, data: dict, temp_client_id: str):
        """Hello メッセージの処理 - クライアント情報を更新"""
        source = data.get('source', 'unknown')
        instance_id = data.get('instance_id', 'unknown')
        live_id = data.get('live_id', '')
        live_title = data.get('live_title', '')

        self.logger.info(f"Hello from {source} (ID: {instance_id}, LiveID: {live_id}, Title: {live_title})")

        # クライアント情報を更新
        if temp_client_id in self.clients:
            client_info = self.clients[temp_client_id]
            client_info.update({
                'instance_id': instance_id,
                'live_id': live_id,
                'live_title': live_title,
                'source': source,
                'is_ncv_plugin': source == 'NCV_Plugin'
            })

            # instance_idをキーにして再登録
            if instance_id != temp_client_id:
                self.clients[instance_id] = client_info
                del self.clients[temp_client_id]

        await websocket.send(json.dumps({
            'type': 'welcome',
            'message': f'Welcome {source}!',
            'server_version': '1.0.0',
            'live_id': live_id
        }))

        return instance_id if instance_id != temp_client_id else temp_client_id

    async def handle_comment(self, websocket, data: dict):
        """コメントメッセージの処理"""
        comment = data.get('comment', '')
        user_id = data.get('user_id', '')
        user_name = data.get('user_name', '')
        live_id = data.get('live_id', '')
        live_title = data.get('live_title', '')
        instance_id = data.get('instance_id', '')
        comment_no = int(data.get('no', 1))  # コメント番号を取得（NCVPluginでは'no'フィールド）

        # LiveID を含めてログに出す
        self.logger.info(
            f"[LiveID={live_id}] Comment from {user_name} ({user_id}): {comment}"
        )

        # データの内容をデバッグ出力
        self.logger.info(f"[COMMENT_DATA] Received comment data: {json.dumps(data, ensure_ascii=False, indent=2)}")

        # デバッグ情報を出力
        self.logger.debug(f"[Debug] Monitored user IDs: {self.monitored_user_ids}")
        self.logger.debug(f"[Debug] User {user_id} in monitored users: {user_id in self.monitored_user_ids}")
        self.logger.debug(f"[Debug] Instance ID: {instance_id}")

        # スペシャルユーザーチェックと自動応答処理
        if user_id in self.monitored_user_ids:
            # スペシャルユーザーが有効かどうかをチェック
            user_cache = self.special_users_cache.get(user_id)
            if user_cache:
                user_config = user_cache['config']
                user_enabled = user_config.get("user_info", {}).get("enabled", True)
                if not user_enabled:
                    self.logger.debug(f"[SpecialUser] User {user_name} ({user_id}) is disabled, skipping")
                    # 確認応答のみ送信
                    await websocket.send(json.dumps({
                        'type': 'ack',
                        'message': 'Comment received (user disabled)',
                        'live_id': live_id
                    }))
                    return

            self.logger.info(f"[SpecialUser] Detected special user: {user_name} ({user_id})")

            response_message = await self.process_special_user_comment(
                user_id, user_name, comment, live_id, instance_id, comment_no, live_number=live_id
            )

            if response_message:
                # スペシャルユーザーの分割送信間隔設定を取得
                user_cache = self.special_users_cache.get(user_id)
                split_delay = 1  # デフォルト値

                if user_cache:
                    user_config = user_cache['config']

                    # デフォルト応答の分割送信間隔を取得
                    default_response = user_config.get('default_response', {})
                    split_delay = default_response.get('response_split_delay_seconds', 1)

                    # 配信者設定の分割送信間隔も確認
                    broadcasters = user_config.get('broadcasters', {})
                    for broadcaster_id, broadcaster_info in broadcasters.items():
                        if broadcaster_info.get('enabled', True):
                            broadcaster_split_delay = broadcaster_info.get('default_response', {}).get('response_split_delay_seconds')
                            if broadcaster_split_delay is not None:
                                split_delay = broadcaster_split_delay
                                break

                # 応答メッセージをNCVプラグインに送信
                await self.send_response_to_ncv_plugin(instance_id, response_message, split_delay)
            else:
                self.logger.debug(f"[SpecialUser] No response generated for: {comment}")

        # 確認応答
        await websocket.send(json.dumps({
            'type': 'ack',
            'message': 'Comment received',
            'live_id': live_id
        }))

        await self.broadcast_comment_to_all_clients(data)

    async def broadcast_comment_to_all_clients(self, comment_data):
        """全クライアントにコメントデータをブロードキャスト"""
        message = json.dumps(comment_data)
        
        # 切断されたクライアントを記録
        dead_clients = []
        
        for client_id, client_info in self.clients.items():
            try:
                await client_info['websocket'].send(message)
            except:
                dead_clients.append(client_id)
        
        # 切断されたクライアントを削除
        for client_id in dead_clients:
            if client_id in self.clients:
                del self.clients[client_id]

    async def handle_list_clients_request(self, websocket):
        """クライアント一覧要求の処理"""
        try:
            ncv_clients = []

            for instance_id, client_info in self.clients.items():
                if client_info.get('is_ncv_plugin', False):
                    ncv_clients.append({
                        'instance_id': instance_id,
                        'source': client_info.get('source', 'unknown'),
                        'live_id': client_info.get('live_id', ''),
                        'live_title': client_info.get('live_title', ''),
                        'address': str(client_info.get('address', '')),
                        'connected_at': client_info.get('connected_at', 0)
                    })

            await websocket.send(json.dumps({
                'type': 'client_list_response',
                'clients': ncv_clients,
                'total_clients': len(ncv_clients)
            }))

            self.logger.info(f"[ClientList] Sent list of {len(ncv_clients)} NCV clients")

        except Exception as e:
            self.logger.error(f"Error handling client list request: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Failed to get client list: {str(e)}'
            }))

    async def handle_send_comment_to_specific_client(self, websocket, data: dict):
        """特定のクライアントにコメントを送信"""
        try:
            target_instance_id = data.get('target_instance_id', '')
            comment_text = data.get('comment', '').strip()
            live_id = data.get('live_id', '')

            if not comment_text:
                await websocket.send(json.dumps({
                    'type': 'send_comment_response',
                    'status': 'error',
                    'message': 'Comment text cannot be empty'
                }))
                return

            if not target_instance_id:
                await websocket.send(json.dumps({
                    'type': 'send_comment_response',
                    'status': 'error',
                    'message': 'Target instance ID is required'
                }))
                return

            # 特定のクライアントに送信
            success, message = await self.send_comment_to_specific_client(target_instance_id, comment_text)

            status = 'success' if success else 'error'
            await websocket.send(json.dumps({
                'type': 'send_comment_response',
                'status': status,
                'message': message,
                'target_instance_id': target_instance_id,
                'comment': comment_text
            }))

        except Exception as e:
            self.logger.error(f"Error handling specific client send: {e}")
            await websocket.send(json.dumps({
                'type': 'send_comment_response',
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }))

    async def send_comment_to_specific_client(self, instance_id: str, comment: str):
        """特定のクライアントにコメントを送信"""
        if instance_id not in self.clients:
            return False, f"Client {instance_id} not found"

        client_info = self.clients[instance_id]

        if not client_info.get('is_ncv_plugin', False):
            return False, f"Client {instance_id} is not an NCV plugin"

        websocket = client_info['websocket']

        try:
            comment_data = {
                'type': 'send_comment_to_ncv',
                'comment': comment,
                'live_id': client_info.get('live_id', ''),
                'timestamp': time.time(),
                'from_python': True,
                'target_instance': instance_id
            }

            await websocket.send(json.dumps(comment_data))

            client_title = client_info.get('live_title', 'Unknown')
            self.logger.info(f"[SpecificSend] Sent to '{client_title}': {comment}")

            return True, f"Comment sent to '{client_title}'"

        except Exception as e:
            return False, f"Failed to send: {str(e)}"

    async def handle_send_comment_result(self, websocket, data: dict, client_id: str):
        """コメント送信結果の処理"""
        status = data.get('status', '')
        comment = data.get('comment', '')
        error = data.get('error', '')

        client_info = self.clients.get(client_id, {})
        client_title = client_info.get('live_title', 'Unknown')

        if status == 'success':
            self.logger.info(f"[SendResult] ✓ '{client_title}' sent successfully: {comment}")
        else:
            self.logger.error(f"[SendResult] ❌ '{client_title}' send failed: {comment}, Error: {error}")

    def load_special_users_config(self):
        """スペシャルユーザー設定を読み込み"""
        try:
            self.logger.info("Loading special users configuration...")

            # 既存のキャッシュをクリア
            self.special_users_cache.clear()
            self.monitored_user_ids.clear()

            # ディレクトリベースの設定を読み込み
            user_dirs = self.config_manager.get_all_user_directories()

            for user_dir in user_dirs:
                user_id = user_dir["user_id"]
                display_name = user_dir["display_name"]

                try:
                    # ユーザー設定を読み込み
                    user_config = self.config_manager.load_user_config_from_directory(user_id, display_name)

                    # 以前の reaction_count を保持
                    old_reaction_count = 0
                    if user_id in self.special_users_cache:
                        old_reaction_count = self.special_users_cache[user_id].get("reaction_count", 0)

                    self.special_users_cache[user_id] = {
                        'config': user_config,
                        'display_name': display_name,
                        'last_loaded': time.time(),
                        'reaction_count': old_reaction_count,
                        'broadcaster_reaction_counts': {} # ←引き継ぎ
                    }

                    # 監視対象に追加
                    self.monitored_user_ids.add(user_id)

                    self.logger.info(f"Loaded config for user {user_id} ({display_name})")

                except Exception as e:
                    self.logger.error(f"Failed to load config for user {user_id}: {str(e)}")

            self.logger.info(f"Special users configuration loaded. Monitoring {len(self.monitored_user_ids)} users")
            self.logger.info(f"Monitored user IDs: {list(self.monitored_user_ids)}")

        except Exception as e:
            self.logger.error(f"Failed to load special users configuration: {str(e)}")

    def reload_user_config(self, user_id: str):
        """特定ユーザーの設定を再読み込み"""
        try:
            if user_id in self.special_users_cache:
                display_name = self.special_users_cache[user_id]['display_name']
                user_config = self.config_manager.load_user_config_from_directory(user_id, display_name)

                self.special_users_cache[user_id] = {
                    'config': user_config,
                    'display_name': display_name,
                    'last_loaded': time.time()
                }

                self.logger.info(f"Reloaded config for user {user_id} ({display_name})")
                return True
            else:
                self.logger.warning(f"User {user_id} not found in cache, performing full reload")
                self.load_special_users_config()
                return True

        except Exception as e:
            self.logger.error(f"Failed to reload config for user {user_id}: {str(e)}")
            return False

    async def handle_reload_user_config(self, websocket, data: dict):
        """設定再読み込みリクエストの処理"""
        user_id = data.get('user_id')

        if user_id:
            success = self.reload_user_config(user_id)
            await websocket.send(json.dumps({
                'type': 'config_reload_response',
                'user_id': user_id,
                'status': 'success' if success else 'error'
            }))
        else:
            # 全ユーザー設定を再読み込み
            self.load_special_users_config()
            await websocket.send(json.dumps({
                'type': 'config_reload_response',
                'status': 'success',
                'message': 'All user configurations reloaded'
            }))

    async def process_special_user_comment(self, user_id: str, user_name: str, comment: str, live_id: str, instance_id: str, comment_no: int = 1, live_title: str = None, live_number: str = None ) -> str:
        """スペシャルユーザーのコメントを処理して応答メッセージを生成"""
        try:
            print(f"[DEBUG] コメント処理: {user_name}({user_id}) → '{comment}'")

            if user_id not in self.special_users_cache:
                self.logger.debug(f"[DEBUG] User {user_id} not found in special_users_cache")
                return None

            user_cache = self.special_users_cache[user_id]
            user_config = user_cache['config']
            self.logger.debug(f"[DEBUG] User config loaded for {user_id}")

            # 最上位階層チェック: スペシャルユーザー自体が無効なら全て無効
            user_info_enabled = user_config.get('user_info', {}).get('enabled', True)
            overall_user_enabled = user_config.get('enabled', True)  # 直接形式もチェック
            user_enabled = user_info_enabled and overall_user_enabled

            self.logger.debug(f"[DEBUG] User enabled check: user_info.enabled={user_info_enabled}, direct.enabled={overall_user_enabled}, final={user_enabled}")
            if not user_enabled:
                self.logger.debug(f"[DEBUG] User {user_id} is disabled at top level, skipping all processing")
                return None

            # === スペシャルトリガーチェック（最優先・反応回数制限より前） ===
            special_triggers_enabled = user_config.get('special_triggers_enabled', False)
            special_triggers = user_config.get('special_triggers', [])

            if special_triggers_enabled and special_triggers:
                self.logger.debug(f"[DEBUG] Checking {len(special_triggers)} special triggers")

                for i, special_trigger in enumerate(special_triggers):
                    if not special_trigger.get('enabled', True):
                        self.logger.debug(f"[DEBUG] Special trigger {i} disabled, skipping")
                        continue

                    self.logger.debug(
                        f"[DEBUG] Checking special trigger {i}: name='{special_trigger.get('name', 'Unnamed')}', "
                        f"keywords={special_trigger.get('keywords', [])}"
                    )

                    # スペシャルトリガーのキーワードマッチング
                    if self.check_trigger_match(special_trigger, comment):
                        self.logger.info(f"[SPECIAL_TRIGGER] Matched special trigger: {special_trigger.get('name', 'Unnamed')}")

                        # 発動確率チェック
                        firing_prob = special_trigger.get('firing_probability', 100)
                        random_roll = random.randint(1, 100)
                        self.logger.debug(f"[DEBUG] Special trigger firing probability check: {random_roll} <= {firing_prob}")

                        if random_roll <= firing_prob:
                            # ignore_all_limitsが有効な場合は反応回数制限を無視
                            ignore_all_limits = special_trigger.get('ignore_all_limits', False)

                            if not ignore_all_limits:
                                # 通常の反応回数制限チェック
                                special_trigger_id = special_trigger.get("id", f"special_trigger_{i}")
                                special_trigger_counts = user_cache.setdefault("special_trigger_reaction_counts", {})
                                st_count = special_trigger_counts.get(special_trigger_id, 0)

                                # スペシャルトリガーの反応回数上限（デフォルトは無制限=999999）
                                max_reactions = special_trigger.get("max_reactions_per_stream", 999999)

                                if st_count >= max_reactions:
                                    self.logger.debug(
                                        f"[DEBUG] Max reactions reached for special trigger {special_trigger_id} "
                                        f"({st_count}/{max_reactions}), skipping response"
                                    )
                                    continue

                                # カウント更新
                                special_trigger_counts[special_trigger_id] = st_count + 1
                            else:
                                self.logger.info(f"[SPECIAL_TRIGGER] ignore_all_limits is enabled, bypassing all reaction limits")

                            # 外部プログラム実行
                            if special_trigger.get("execute_program", False):
                                self.execute_external_program(special_trigger, user_name, user_id, comment, live_id)

                            # 応答メッセージ生成
                            response = self.generate_response_message(
                                special_trigger, user_name, comment, None, comment_no, user_id
                            )
                            self.logger.info(f"[SPECIAL_TRIGGER] Generated response: {response}")
                            return response
                        else:
                            self.logger.debug(f"[DEBUG] Special trigger failed firing probability check")

            # === スペシャルトリガーでマッチしなかった場合、通常の反応回数制限をチェック ===
            # ユーザー単位の反応カウントを取得
            reaction_count = user_cache.get("reaction_count", 0)

            # デフォルト応答の上限を取得（ユーザー単位）
            default_response = user_config.get("default_response", {})
            max_reactions = default_response.get("max_reactions_per_stream", 1)

            if reaction_count >= max_reactions:
                self.logger.debug(f"[DEBUG] Max reactions reached for user {user_id} ({reaction_count}/{max_reactions}), skipping response")
                return None

            # カウント更新
            user_cache["reaction_count"] = reaction_count + 1

            # 配信者設定を取得（簡略化：最初の有効な配信者を使用）
            broadcasters = user_config.get('broadcasters', {})
            self.logger.debug(f"[DEBUG] Broadcasters found: {list(broadcasters.keys())}")

            active_broadcaster = None
            active_broadcaster_id = None

            for broadcaster_id, broadcaster_config in broadcasters.items():
                self.logger.debug(f"[DEBUG] Checking broadcaster {broadcaster_id}, enabled: {broadcaster_config.get('enabled', True)}")
                if broadcaster_config.get('enabled', True):
                    active_broadcaster = broadcaster_config
                    active_broadcaster_id = broadcaster_id
                    self.logger.debug(f"[DEBUG] Selected active broadcaster: {broadcaster_id}")
                    break

            # === 配信者ごとの最大反応数チェック追加 ===
            if active_broadcaster_id:
                # 配信者ごとのカウントを取得
                br_counts = user_cache.setdefault("broadcaster_reaction_counts", {})
                br_count = br_counts.get(active_broadcaster_id, 0)

                # 配信者デフォルト応答の上限を取得
                br_default_response = active_broadcaster.get("default_response", {})
                br_max_reactions = br_default_response.get("max_reactions_per_stream", 1)

                if br_count >= br_max_reactions:
                    self.logger.debug(
                        f"[DEBUG] Max reactions reached for broadcaster {active_broadcaster_id} "
                        f"({br_count}/{br_max_reactions}), skipping response"
                    )
                    return None

                # カウント更新
                br_counts[active_broadcaster_id] = br_count + 1

            if not active_broadcaster:
                self.logger.debug(f"[DEBUG] No active broadcaster found, checking user default response")
                # デフォルト応答を試行（有効で定型メッセージがあれば使用）
                default_response = user_config.get('default_response', {})
                default_enabled = default_response.get('enabled', True)
                messages = default_response.get('messages', [])
                self.logger.debug(f"[DEBUG] User default response enabled: {default_enabled}, messages: {messages}")
                if default_enabled and messages:
                    response = self.generate_response_message(default_response, user_name, comment, None, comment_no, user_id)
                    self.logger.debug(f"[DEBUG] Generated user default response: {response}")
                    return response
                self.logger.debug(f"[DEBUG] User default response disabled or no messages available")
                return None

            # 中間階層チェック: 配信者が無効なら配信者関連のすべてを無効
            broadcaster_enabled = active_broadcaster.get('enabled', True)
            self.logger.debug(f"[DEBUG] Active broadcaster {active_broadcaster_id} enabled: {broadcaster_enabled}")
            if not broadcaster_enabled:
                self.logger.debug(f"[DEBUG] Broadcaster {active_broadcaster_id} is disabled, skipping broadcaster-level processing")
                # 配信者が無効の場合、ユーザーデフォルト応答を試行
                default_response = user_config.get('default_response', {})
                default_enabled = default_response.get('enabled', True)
                messages = default_response.get('messages', [])
                self.logger.debug(f"[DEBUG] Fallback to user default response enabled: {default_enabled}, messages: {messages}")
                if default_enabled and messages:
                    response = self.generate_response_message(default_response, user_name, comment, None, comment_no, user_id)
                    self.logger.debug(f"[DEBUG] Generated fallback user default response: {response}")
                    return response
                self.logger.debug(f"[DEBUG] No fallback response available")
                return None

            # トリガーチェック（配信者が有効な場合のみ実行）
            triggers = active_broadcaster.get('triggers', [])
            self.logger.debug(f"[DEBUG] Active broadcaster has {len(triggers)} triggers")

            for i, trigger in enumerate(triggers):
                if not trigger.get('enabled', True):
                    self.logger.debug(f"[DEBUG] Trigger {i} disabled, skipping")
                    continue

                self.logger.debug(
                    f"[DEBUG] Checking trigger {i}: name='{trigger.get('name', 'Unnamed')}', keywords={trigger.get('keywords', [])}"
                )

                # === トリガーごとの反応回数チェック追加 ===
                trigger_id = trigger.get("id", f"trigger_{i}")
                trigger_counts = user_cache.setdefault("trigger_reaction_counts", {})
                trig_count = trigger_counts.get(trigger_id, 0)

                max_reactions = trigger.get("max_reactions_per_stream", 1)
                if trig_count >= max_reactions:
                    self.logger.debug(
                        f"[DEBUG] Max reactions reached for trigger {trigger_id} "
                        f"({trig_count}/{max_reactions}), skipping response"
                    )
                    continue  # このトリガーはこれ以上反応しない

                if self.check_trigger_match(trigger, comment):
                    self.logger.debug(f"[DEBUG] Trigger {i} matched!")
                    # 発動確率チェック
                    firing_prob = trigger.get('firing_probability', 100)
                    random_roll = random.randint(1, 100)
                    self.logger.debug(f"[DEBUG] Firing probability check: {random_roll} <= {firing_prob}")
                    if random_roll <= firing_prob:
                        # カウント更新
                        trigger_counts[trigger_id] = trig_count + 1

                        response = self.generate_response_message(
                            trigger, user_name, comment, active_broadcaster, comment_no, user_id
                        )
                        self.logger.debug(f"[DEBUG] Generated trigger response: {response}")
                        return response
                    else:
                        self.logger.debug(f"[DEBUG] Trigger failed firing probability check")


            # デフォルト応答チェック
            default_response = active_broadcaster.get('default_response', {})
            self.logger.debug(f"[DEBUG] Checking broadcaster default response, enabled: {default_response.get('enabled', False)}")
            if default_response.get('enabled', False):
                response = self.generate_response_message(default_response, user_name, comment, active_broadcaster, comment_no, user_id)
                self.logger.debug(f"[DEBUG] Generated broadcaster default response: {response}")
                return response

            self.logger.debug(f"[DEBUG] No response generated - no matching triggers or default responses")
            return None

        except Exception as e:
            self.logger.error(f"Error processing special user comment: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def execute_external_program(self, trigger: dict, user_name: str, user_id: str, comment: str, live_id: str):
        """外部プログラムを実行"""
        try:
            program_path = trigger.get("program_path", "").strip()
            program_args = trigger.get("program_args", "").strip()

            if not program_path:
                self.logger.warning(f"[EXTERNAL_PROGRAM] Program path is empty, skipping execution")
                return

            # 変数を置換
            replacements = {
                "{user_name}": user_name,
                "{user_id}": user_id,
                "{comment}": comment,
                "{live_id}": live_id
            }

            for key, value in replacements.items():
                program_args = program_args.replace(key, value)

            # コマンドを構築
            if program_args:
                cmd = [program_path] + program_args.split()
            else:
                cmd = [program_path]

            self.logger.info(f"[EXTERNAL_PROGRAM] Executing: {' '.join(cmd)}")

            # プログラムを実行（非同期・バックグラウンド）
            subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            self.logger.info(f"[EXTERNAL_PROGRAM] Successfully launched: {program_path}")

        except Exception as e:
            self.logger.error(f"[EXTERNAL_PROGRAM] Failed to execute program: {str(e)}")
            import traceback
            traceback.print_exc()

    def check_trigger_match(self, trigger: dict, comment: str) -> bool:
        """トリガーがコメントにマッチするかチェック"""
        keywords = trigger.get('keywords', [])
        keyword_condition = trigger.get('keyword_condition', 'OR')

        self.logger.debug(f"[DEBUG] check_trigger_match: keywords={keywords}, condition={keyword_condition}, comment='{comment}'")

        if not keywords:
            self.logger.debug(f"[DEBUG] No keywords defined for trigger")
            return False

        comment_lower = comment.lower()

        if keyword_condition == 'AND':
            result = all(keyword.lower() in comment_lower for keyword in keywords)
            self.logger.debug(f"[DEBUG] AND condition result: {result}")
            return result
        else:  # OR
            matches = [(keyword, keyword.lower() in comment_lower) for keyword in keywords]
            result = any(match[1] for match in matches)
            self.logger.debug(f"[DEBUG] OR condition matches: {matches}, result: {result}")
            return result

    def generate_response_message(self, response_config: dict, user_name: str, comment: str, broadcaster_config: dict = None, comment_no: int = 1, user_id: str = '',live_title: str = None, live_number: str = None ) -> str:
        """応答メッセージを生成"""
        try:
            response_type = response_config.get('response_type', 'predefined')
            self.logger.debug(f"[DEBUG] generate_response_message: response_type={response_type}")

            if response_type == 'predefined':
                messages = response_config.get('messages', [])
                self.logger.debug(f"[DEBUG] Predefined messages available: {messages}")

                if messages:
                    # ランダムにメッセージを選択
                    message = random.choice(messages)
                    self.logger.debug(f"[DEBUG] Selected message template: '{message}'")

                    # テンプレート変数を置換
                    original_message = message
                    self.logger.info(f"[TEMPLATE] Original message: '{original_message}'")
                    self.logger.info(f"[TEMPLATE] Comment number to replace: {comment_no}")

                    # ログファイルに確実に出力されるよう強制フラッシュ
                    for handler in self.logger.handlers:
                        if hasattr(handler, 'flush'):
                            handler.flush()
                    # 時間情報を取得
                    import datetime
                    now = datetime.datetime.now()
                    current_time = now.strftime("%H:%M:%S")
                    current_date = now.strftime("%Y-%m-%d")
                    current_datetime = now.strftime("%Y-%m-%d %H:%M:%S")

                    # 全テンプレート変数を置換
                    message = message.replace('{no}', str(comment_no))  # {no} 形式
                    message = message.replace('{{no}}', str(comment_no))  # コメント番号
                    message = message.replace('{{user_name}}', user_name)  # ユーザー名
                    message = message.replace('{user_name}', user_name)  # {user_name} 形式
                    message = message.replace('{{user_id}}', user_id)  # ユーザーID
                    message = message.replace('{user_id}', user_id)  # {user_id} 形式
                    message = message.replace('{{comment_content}}', comment)  # コメント内容
                    message = message.replace('{comment_content}', comment)  # {comment_content} 形式
                    message = message.replace('{{time}}', current_time)  # 現在時刻 (HH:MM:SS)
                    message = message.replace('{time}', current_time)  # {time} 形式
                    message = message.replace('{{date}}', current_date)  # 現在日付 (YYYY-MM-DD)
                    message = message.replace('{date}', current_date)  # {date} 形式
                    message = message.replace('{{datetime}}', current_datetime)  # 現在日時
                    message = message.replace('{datetime}', current_datetime)  # {datetime} 形式

                    if broadcaster_config:
                        broadcaster_name = broadcaster_config.get('broadcaster_name', 'Unknown')
                        message = message.replace('{{broadcaster_name}}', broadcaster_name)  # 配信者名
                        message = message.replace('{broadcaster_name}', broadcaster_name)  # {broadcaster_name} 形式
                        self.logger.info(f"[TEMPLATE] Using broadcaster_name: {broadcaster_name}")

                    self.logger.info(f"[TEMPLATE] Final message after template replacement: '{message}'")

                    # ログファイルに確実に出力されるよう強制フラッシュ
                    for handler in self.logger.handlers:
                        if hasattr(handler, 'flush'):
                            handler.flush()

                    return message
                else:
                    self.logger.debug(f"[DEBUG] No predefined messages available")

            # AI応答の場合
            elif response_type == 'ai':
                self.logger.debug(f"[DEBUG] Using AI response")
                ai_prompt = response_config.get('ai_response_prompt', '')
                if ai_prompt:
                    ai_response = self.generate_ai_response(ai_prompt, user_name, comment, user_id, broadcaster_config, comment_no, trigger_content=comment, lv_title=live_title,lv_number=None)
                    if ai_response:
                        return ai_response
                    else:
                        self.logger.warning(f"[AI] Failed to generate AI response, falling back to default")
                        return f">>{comment_no} {user_name}さん、コメントありがとうございます！"
                else:
                    self.logger.warning(f"[AI] No AI prompt configured")
                    return f">>{comment_no} {user_name}さん、コメントありがとうございます！"

            self.logger.debug(f"[DEBUG] No response generated from generate_response_message")
            return None

        except Exception as e:
            self.logger.error(f"Error generating response message: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def generate_ai_response(self, prompt_template: str, user_name: str, comment: str, user_id: str, broadcaster_config: dict = None, comment_no: int = 1, trigger_content: str = None, lv_title: str = None, lv_number=None) -> str:
        """AI応答を生成"""
        try:
            print(f"[DEBUG] AI応答生成: プロンプト='{prompt_template}'")
            log_to_gui("AIに応答を生成中...")

            # グローバル設定を取得
            global_config = self.config_manager.load_global_config()
            api_settings = global_config.get('api_settings', {})

            # API設定を取得
            model = api_settings.get('response_ai_model', 'openai-gpt4o')
            api_key = api_settings.get('response_api_key', '')
            max_chars = api_settings.get('response_max_characters', 100)

            if not api_key:
                self.logger.warning("[AI] No API key configured")
                return None

            # 時間情報を取得
            import datetime
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M:%S")
            current_date = now.strftime("%Y-%m-%d")
            current_datetime = now.strftime("%Y-%m-%d %H:%M:%S")

            # プロンプトのテンプレート変数を置換
            prompt = prompt_template

            prompt = prompt.replace('{{no}}', str(comment_no))
            prompt = prompt.replace('{no}', str(comment_no))
            prompt = prompt.replace('{{user_name}}', user_name)
            prompt = prompt.replace('{user_name}', user_name)
            prompt = prompt.replace('{{user_id}}', user_id)
            prompt = prompt.replace('{user_id}', user_id)
            prompt = prompt.replace('{{comment_content}}', comment)
            prompt = prompt.replace('{comment_content}', comment)

            # trigger_contentがある場合は使用、なければcommentをフォールバック
            actual_trigger_content = trigger_content if trigger_content is not None else comment
            prompt = prompt.replace('{{trigger_content}}', actual_trigger_content)
            prompt = prompt.replace('{trigger_content}', actual_trigger_content)
            prompt = prompt.replace('{{time}}', current_time)
            prompt = prompt.replace('{time}', current_time)
            prompt = prompt.replace('{{date}}', current_date)
            prompt = prompt.replace('{date}', current_date)
            prompt = prompt.replace('{{datetime}}', current_datetime)
            prompt = prompt.replace('{datetime}', current_datetime)

            # lv_title変数の置換
            if lv_title:
                prompt = prompt.replace('{{lv_title}}', lv_title)
                prompt = prompt.replace('{lv_title}', lv_title)

            if broadcaster_config:
                broadcaster_name = broadcaster_config.get('broadcaster_name', 'Unknown')
                self.logger.debug(f"[AI DEBUG] broadcaster_name: '{broadcaster_name}'")
                prompt = prompt.replace('{{broadcaster_name}}', broadcaster_name)
                prompt = prompt.replace('{broadcaster_name}', broadcaster_name)
                self.logger.debug(f"[AI DEBUG] After broadcaster replacement: '{prompt}'")

            print(f"[DEBUG] API呼び出し: '{prompt}' → {model}")

            # OpenAI API呼び出し
            if model.startswith('openai-'):
                actual_model = model.replace('openai-', '')
                response = self.call_openai_api(api_key, actual_model, prompt, max_chars)
            else:
                self.logger.warning(f"[AI] Unsupported model: {model}")
                return None

            if response:
                # 改行を削除して一行にまとめる
                single_line_response = ' '.join(line.strip() for line in response.split('\n') if line.strip())
                print(f"[DEBUG] AI応答({len(single_line_response)}文字): {single_line_response}")
                log_to_gui(f"AI応答を生成しました: {single_line_response[:30]}{'...' if len(single_line_response) > 30 else ''}")

                if single_line_response:
                    return single_line_response
                else:
                    return response
            else:
                self.logger.debug(f"[AI DEBUG] No response generated")
                return None

        except Exception as e:
            self.logger.error(f"Error generating AI response: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def call_openai_api(self, api_key: str, model: str, prompt: str, max_chars: int) -> str:
        """OpenAI APIを呼び出し"""
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # モデル名の変換
            openai_model = 'gpt-4o' if model == 'gpt4o' else model

            data = {
                'model': openai_model,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': min(max_chars * 2, 150),  # 余裕を持たせる
                'temperature': 0.7
            }

            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()

                # 文字数制限を適用
                if len(ai_response) > max_chars:
                    ai_response = ai_response[:max_chars-3] + "..."

                return ai_response
            else:
                self.logger.error(f"[AI] OpenAI API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Error calling OpenAI API: {str(e)}")
            return None

    async def send_response_to_ncv_plugin(self, instance_id: str, response_message: str, split_delay: float = None):
        """NCVプラグインに応答メッセージを送信（必要に応じてメッセージを分割）"""
        try:
            # split_delayが指定されていない場合はグローバル設定から取得
            if split_delay is None:
                global_config = self.config_manager.load_global_config()
                api_settings = global_config.get('api_settings', {})
                split_delay = api_settings.get('response_split_delay_seconds', 1)

            # 70文字以内の場合はそのまま送信
            print(f"[DEBUG] 文字数判定: {len(response_message)}文字 vs 70文字")
            if len(response_message) <= 70:
                print(f"[DEBUG] 単一送信({len(response_message)}文字): {response_message}")
                success, message = await self.send_comment_to_specific_client(instance_id, response_message)
                if success:
                    print(f"[DEBUG] ✓ 送信成功")
                    log_to_gui(f"コメントを送信しました: {response_message}")
                else:
                    print(f"[DEBUG] ✗ 送信失敗: {message}")
                    log_to_gui(f"コメント送信が失敗しました: {message}")
                return

            # 70文字を超える場合は分割して送信
            print(f"[DEBUG] 分割送信({len(response_message)}文字, {split_delay}秒間隔):")

            # メッセージを70文字ずつに分割
            parts = []
            remaining_message = response_message
            part_number = 1

            while remaining_message:
                if len(remaining_message) <= 70:
                    # 最後の部分
                    parts.append(remaining_message)
                    break
                else:
                    # 70文字で切り取り、できるだけ句読点や空白で区切る
                    cut_pos = 70
                    # より自然な位置で分割するため、句読点や空白を探す
                    for i in range(min(60, len(remaining_message)-10), min(70, len(remaining_message))):
                        if remaining_message[i] in ['。', '！', '？', '、', ' ', '　']:
                            cut_pos = i + 1
                            break

                    part = remaining_message[:cut_pos]
                    parts.append(part)
                    remaining_message = remaining_message[cut_pos:]
                    part_number += 1

            # 各部分を順次送信
            for i, part in enumerate(parts):
                print(f"[DEBUG] パート{i+1}/{len(parts)}: '{part}'")
                success, message = await self.send_comment_to_specific_client(instance_id, part)
                if success:
                    print(f"[DEBUG] ✓ 送信成功")
                else:
                    print(f"[DEBUG] ✗ 送信失敗: {message}")

                # 最後の部分以外は遅延を入れる
                if i < len(parts) - 1:
                    print(f"[DEBUG] {split_delay}秒待機...")
                    await asyncio.sleep(split_delay)

            print(f"[DEBUG] 分割送信完了({len(parts)}パート)")
            log_to_gui(f"分割コメントを送信完了しました ({len(parts)}パート)")

        except Exception as e:
            self.logger.error(f"Error sending response to NCV plugin: {str(e)}")

    async def start(self, host='localhost', port=8766):
        """サーバー起動"""
        import sys
        self.logger.info(f"Starting WebSocket server on ws://{host}:{port}")
        
        try:
            # websocketsのバージョンチェック
            version_parts = websockets.__version__.split('.')
            major_version = int(version_parts[0])
            
            if major_version >= 11:
                # v11以降の新しい方式
                async with websockets.serve(self.handler, host, port):
                    self.logger.info(f"Server listening on {host}:{port} (websockets v{websockets.__version__})")
                    await asyncio.Future()  # 永続実行
            else:
                # v10以前の古い方式
                server = await websockets.serve(self.handler, host, port)
                self.logger.info(f"Server listening on {host}:{port} (websockets v{websockets.__version__})")
                await asyncio.Future()  # 永続実行

        except OSError as e:
            if e.errno == 10048:
                self.logger.error(f"❌ ポート {port} は既に使用中です。別のインスタンスが動作中と判断して終了します。")
                sys.exit(1)
            else:
                raise


async def main():
    # ログ設定
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/ncv_ws_server.log', encoding='utf-8')
        ]
    )
    
    # サーバー起動
    server = NCVCommentServer()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())