import asyncio
import json
import logging
import websockets
from typing import Optional, Dict
import threading
import time

class NCVCommentServer:
    def __init__(self):
        self.clients = {}  # instance_id をキーにしたクライアント辞書
        self.logger = logging.getLogger(__name__)
        self.config = self.load_config()
        self.pending_comments = []
        
    def load_config(self):
        """設定ファイル読み込み"""
        try:
            import os
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            
            default_config = {
                "comment_send_enabled": True,
                "comment_interval_seconds": 3,
                "debug_log_enabled": True
            }
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            else:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                self.logger.info("Created default config.json")
                
            return default_config
        except Exception as e:
            self.logger.error(f"Config load error: {e}")
            return {
                "comment_send_enabled": True,
                "comment_interval_seconds": 3,
                "debug_log_enabled": True
            }
        
    async def handler(self, websocket, *args):
        """WebSocket接続ハンドラー"""
        path = args[0] if args else None
        client_id = None
        temp_id = f"temp_{len(self.clients)}_{int(time.time())}"
        
        try:
            # 一時的なクライアント情報を作成
            client_info = {
                'websocket': websocket,
                'address': websocket.remote_address,
                'path': path,
                'instance_id': None,
                'live_id': None,
                'live_title': None,
                'source': 'unknown',
                'connected_at': time.time(),
                'is_ncv_plugin': False  # NCVプラグインかGUIクライアントかを区別
            }
            
            self.clients[temp_id] = client_info
            self.logger.info(f"Client connected from {client_info['address']}")
            
            await websocket.send(json.dumps({
                'type': 'connection',
                'status': 'connected',
                'message': 'Connected to NCV Comment Server'
            }))
            
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
            elif client_id and client_id in self.clients:
                del self.clients[client_id]
            self.logger.info(f"Client removed from pool")

    async def process_message(self, websocket, message: str, current_client_id: str):
        """受信メッセージの処理"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if self.config["debug_log_enabled"]:
                self.logger.debug(f"Received message type: {msg_type}")
            
            if msg_type == 'hello':
                return await self.handle_hello(websocket, data, current_client_id)
            elif msg_type == 'ncv_comment':
                await self.handle_comment(websocket, data, current_client_id)
            elif msg_type == 'send_comment_request':
                await self.handle_send_comment_request(websocket, data)
            elif msg_type == 'send_comment_to_specific_client':
                await self.handle_send_comment_to_specific_client(websocket, data)
            elif msg_type == 'send_comment_result':
                await self.handle_send_comment_result(websocket, data, current_client_id)
            elif msg_type == 'list_clients_request':
                await self.handle_list_clients_request(websocket)
            elif msg_type == 'get_client_info_request':
                await self.handle_get_client_info_request(websocket, data)
            elif msg_type == 'get_client_info_response':
                await self.handle_get_client_info_response(websocket, data, current_client_id)
            elif msg_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
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
            'live_id': live_id,
            'comment_send_enabled': self.config["comment_send_enabled"]
        }))
        
        return instance_id if instance_id != temp_client_id else temp_client_id

    async def handle_comment(self, websocket, data: dict, client_id: str):
        """コメントメッセージの処理"""
        comment = data.get('comment', '')
        user_id = data.get('user_id', '')
        user_name = data.get('user_name', '')
        live_id = data.get('live_id', '')

        self.logger.info(
            f"[LiveID={live_id}] Comment from {user_name} ({user_id}): {comment}"
        )

        await websocket.send(json.dumps({
            'type': 'ack',
            'message': 'Comment received',
            'live_id': live_id
        }))

    async def handle_send_comment_request(self, websocket, data: dict):
        """コメント送信リクエストの処理（全クライアントに送信）"""
        try:
            if not self.config["comment_send_enabled"]:
                await websocket.send(json.dumps({
                    'type': 'send_comment_error',
                    'message': 'Comment sending is disabled'
                }))
                return
            
            comment_text = data.get('comment', '').strip()
            live_id = data.get('live_id', '')
            
            if not comment_text:
                await websocket.send(json.dumps({
                    'type': 'send_comment_error',
                    'message': 'Comment text cannot be empty'
                }))
                return
            
            comment_request = {
                'type': 'send_comment_to_ncv',
                'comment': comment_text,
                'live_id': live_id,
                'timestamp': time.time(),
                'from_python': True
            }
            
            # NCVプラグインクライアントにのみ送信
            await self.broadcast_to_ncv_clients(comment_request)
            
            self.logger.info(f"[SendComment] Broadcast to all NCV clients: {comment_text}")
            
            await websocket.send(json.dumps({
                'type': 'send_comment_response',
                'status': 'queued',
                'message': f'Comment sent to all NCV clients: {comment_text}',
                'live_id': live_id
            }))
            
        except Exception as e:
            self.logger.error(f"Error handling send comment request: {e}")
            await websocket.send(json.dumps({
                'type': 'send_comment_error',
                'message': f'Server error: {str(e)}'
            }))

    async def handle_send_comment_to_specific_client(self, websocket, data: dict):
        """特定のクライアントにコメントを送信"""
        try:
            if not self.config["comment_send_enabled"]:
                await websocket.send(json.dumps({
                    'type': 'send_comment_error',
                    'message': 'Comment sending is disabled'
                }))
                return
            
            target_instance_id = data.get('target_instance_id', '')
            comment_text = data.get('comment', '').strip()
            live_id = data.get('live_id', '')
            
            if not comment_text:
                await websocket.send(json.dumps({
                    'type': 'send_comment_error',
                    'message': 'Comment text cannot be empty'
                }))
                return
                
            if not target_instance_id:
                await websocket.send(json.dumps({
                    'type': 'send_comment_error',
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
                'type': 'send_comment_error',
                'message': f'Server error: {str(e)}'
            }))

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

    async def broadcast_to_ncv_clients(self, message_data: dict):
        """NCVクライアントにのみブロードキャスト"""
        ncv_clients = [
            client_info for client_info in self.clients.values() 
            if client_info.get('is_ncv_plugin', False)
        ]
        
        if not ncv_clients:
            self.logger.warning("No NCV clients connected for broadcast")
            return
            
        message = json.dumps(message_data)
        disconnected_clients = []
        
        for client_info in ncv_clients:
            try:
                await client_info['websocket'].send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client_info)
            except Exception as e:
                self.logger.error(f"Error broadcasting to NCV client: {e}")
                disconnected_clients.append(client_info)
        
        # 切断されたクライアントを削除
        for client_info in disconnected_clients:
            instance_id = client_info.get('instance_id')
            if instance_id and instance_id in self.clients:
                del self.clients[instance_id]

    async def start(self, host='localhost', port=8766):
        """サーバー起動"""
        import sys
        self.logger.info(f"Starting WebSocket server on ws://{host}:{port}")
        
        try:
            version_parts = websockets.__version__.split('.')
            major_version = int(version_parts[0])
            
            if major_version >= 11:
                async with websockets.serve(self.handler, host, port):
                    self.logger.info(f"Server listening on {host}:{port} (websockets v{websockets.__version__})")
                    self.logger.info("Use comment_sender_gui.py to send comments to specific NCV instances")
                    await asyncio.Future()
            else:
                server = await websockets.serve(self.handler, host, port)
                self.logger.info(f"Server listening on {host}:{port} (websockets v{websockets.__version__})")
                self.logger.info("Use comment_sender_gui.py to send comments to specific NCV instances")
                await asyncio.Future()

        except OSError as e:
            if e.errno == 10048:
                self.logger.error(f"❌ ポート {port} は既に使用中です。")
                sys.exit(1)
            else:
                raise
    async def handle_get_client_info_request(self, websocket, data: dict):
        """クライアント情報要求の処理（サーバー側でも対応）"""
        try:
            instance_id = data.get('instance_id', '')
            
            if instance_id in self.clients:
                client_info = self.clients[instance_id]
                
                # 最新情報を要求（実際にはC#側が応答する）
                self.logger.info(f"[ClientInfoRequest] Request for {instance_id} forwarded to client")
                
                # クライアントに転送
                target_websocket = client_info['websocket']
                await target_websocket.send(json.dumps(data))
            else:
                self.logger.warning(f"[ClientInfoRequest] Client {instance_id} not found")
                
        except Exception as e:
            self.logger.error(f"Error handling client info request: {e}")

    async def handle_get_client_info_response(self, websocket, data: dict, client_id: str):
        """クライアント情報応答の処理"""
        try:
            instance_id = data.get('instance_id', '')
            live_id = data.get('live_id', '')
            live_title = data.get('live_title', '')
            
            if instance_id in self.clients:
                # クライアント情報を更新
                client_info = self.clients[instance_id]
                
                # "unknown" でない場合のみ更新
                if live_id and live_id.lower() != 'unknown':
                    client_info['live_id'] = live_id
                if live_title and live_title.lower() != 'unknown':
                    client_info['live_title'] = live_title
                    
                self.logger.info(f"[ClientInfoResponse] Updated {instance_id}: title='{live_title}', id='{live_id}'")
            
        except Exception as e:
            self.logger.error(f"Error handling client info response: {e}")



async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ncv_ws_server.log', encoding='utf-8')
        ]
    )
    
    server = NCVCommentServer()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())