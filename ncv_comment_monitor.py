import asyncio
import json
import logging
import websockets
from typing import Optional

class NCVCommentServer:
    def __init__(self):
        self.clients = set()
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
        
        try:
            self.clients.add(websocket)
            self.logger.info(f"Client connected from {client_info['address']}")
            
            # 接続確認メッセージを送信
            await websocket.send(json.dumps({
                'type': 'connection',
                'status': 'connected',
                'message': 'Connected to NCV Comment Server'
            }))
            
            # メッセージ受信ループ
            async for message in websocket:
                await self.process_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosedOK:
            self.logger.info(f"Client disconnected normally: {client_info['address']}")
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.warning(f"Client disconnected with error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in handler: {e}", exc_info=True)
        finally:
            if websocket in self.clients:
                self.clients.remove(websocket)
                self.logger.info(f"Client removed from pool: {client_info['address']}")

    async def process_message(self, websocket, message: str):
        """受信メッセージの処理"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            self.logger.debug(f"Received message type: {msg_type}")
            
            if msg_type == 'hello':
                await self.handle_hello(websocket, data)
            elif msg_type == 'ncv_comment':
                await self.handle_comment(websocket, data)
            elif msg_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
            else:
                self.logger.warning(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON received: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)

    async def handle_hello(self, websocket, data: dict):
        """Hello メッセージの処理"""
        source = data.get('source', 'unknown')
        instance_id = data.get('instance_id', 'unknown')
        live_id = data.get('live_id', '')

        self.logger.info(f"Hello from {source} (ID: {instance_id}, LiveID: {live_id})")

        # 応答を送信
        await websocket.send(json.dumps({
            'type': 'welcome',
            'message': f'Welcome {source}!',
            'server_version': '1.0.0',
            'live_id': live_id
        }))

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