import asyncio
import json
import logging
import websockets
from typing import Optional

class NCVCommentServer:
    def __init__(self):
        self.clients = {}  # instance_id をキーにしたクライアント辞書
        self.logger = logging.getLogger(__name__)
        
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
        
        temp_id = f"temp_{len(self.clients)}_{int(__import__('time').time())}"

        try:
            # 一時的なクライアント情報を作成
            client_info.update({
                'instance_id': None,
                'live_id': None,
                'live_title': None,
                'source': 'unknown',
                'connected_at': __import__('time').time(),
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

        # LiveID を含めてログに出す
        self.logger.info(
            f"[LiveID={live_id}] Comment from {user_name} ({user_id}): {comment}"
        )

        # 必要に応じて処理（DBへの保存、他クライアントへの転送など）

        # 確認応答
        await websocket.send(json.dumps({
            'type': 'ack',
            'message': 'Comment received',
            'live_id': live_id
        }))

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
                'timestamp': __import__('time').time(),
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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ncv_ws_server.log', encoding='utf-8')
        ]
    )
    
    # サーバー起動
    server = NCVCommentServer()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())