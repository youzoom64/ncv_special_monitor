# comment_sender_gui.py - デバッグ強化版
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import asyncio
import websockets
import json
import threading
from datetime import datetime
import time

class CommentSenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NCV Comment Sender")
        self.root.geometry("600x500")
        
        self.server_uri = "ws://127.0.0.1:8766"
        self.clients = []
        self.selected_client = None
        self.auto_refresh = True
        
        self.setup_ui()
        self.start_auto_refresh()
        
    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # クライアント選択セクション
        ttk.Label(main_frame, text="Select NCV Client:", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 5)
        )
        
        # クライアント一覧
        client_frame = ttk.Frame(main_frame)
        client_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        client_frame.columnconfigure(0, weight=1)
        
        # クライアントリストボックス
        self.client_listbox = tk.Listbox(client_frame, height=6, font=("Consolas", 9))
        self.client_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.client_listbox.bind('<<ListboxSelect>>', self.on_client_select)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(client_frame, orient=tk.VERTICAL, command=self.client_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.client_listbox.configure(yscrollcommand=scrollbar.set)
        
        # リフレッシュボタンと自動更新チェック
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.refresh_button = ttk.Button(control_frame, text="Refresh Clients", command=self.refresh_clients)
        self.refresh_button.grid(row=0, column=0, padx=(0, 10))
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        self.auto_refresh_check = ttk.Checkbutton(
            control_frame, text="Auto-refresh every 5s", 
            variable=self.auto_refresh_var, command=self.toggle_auto_refresh
        )
        self.auto_refresh_check.grid(row=0, column=1)
        
        # 選択中のクライアント表示
        self.selected_label = ttk.Label(main_frame, text="No client selected", foreground="red")
        self.selected_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # コメント入力セクション
        comment_frame = ttk.LabelFrame(main_frame, text="Send Comment", padding="10")
        comment_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        comment_frame.columnconfigure(0, weight=1)
        comment_frame.rowconfigure(0, weight=1)
        
        # コメント入力
        self.comment_text = scrolledtext.ScrolledText(comment_frame, height=4, width=50, font=("Arial", 11))
        self.comment_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        self.comment_text.bind('<Control-Return>', lambda e: self.send_comment())
        
        # 送信ボタンフレーム
        button_frame = ttk.Frame(comment_frame)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.send_button = ttk.Button(button_frame, text="Send Comment (Ctrl+Enter)", command=self.send_comment)
        self.send_button.grid(row=0, column=0, padx=(0, 10))
        
        self.clear_button = ttk.Button(button_frame, text="Clear", command=self.clear_comment)
        self.clear_button.grid(row=0, column=1)
        
        # ログセクション
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=50, state=tk.DISABLED, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 初期状態でコメント入力を無効化
        self.set_comment_input_state(False)
        
    def start_auto_refresh(self):
        """自動リフレッシュを開始"""
        self.refresh_clients()
        
        def auto_refresh_loop():
            while True:
                time.sleep(5)
                if self.auto_refresh:
                    self.root.after(0, self.refresh_clients)
        
        refresh_thread = threading.Thread(target=auto_refresh_loop, daemon=True)
        refresh_thread.start()
        
    def toggle_auto_refresh(self):
        """自動リフレッシュのON/OFF"""
        self.auto_refresh = self.auto_refresh_var.get()
        
    def refresh_clients(self):
        """クライアント一覧を更新"""
        self.refresh_button.config(state=tk.DISABLED, text="Refreshing...")
        
        thread = threading.Thread(target=self._refresh_clients_async, daemon=True)
        thread.start()
        
    def _refresh_clients_async(self):
        """非同期でクライアント一覧を取得"""
        try:
            success = asyncio.run(self._get_client_list())
            self.root.after(0, lambda: self._update_client_list(success))
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Refresh error: {e}"))
            self.root.after(0, lambda: self.refresh_button.config(state=tk.NORMAL, text="Refresh Clients"))
            
    async def _get_client_list(self):
        """サーバーからクライアント一覧を取得"""
        try:
            self.log_message("🔄 Connecting to server...")
            async with websockets.connect(self.server_uri, open_timeout=5) as websocket:
                self.log_message("✓ Connected, requesting client list...")

                # 一覧リクエスト
                request = {'type': 'list_clients_request'}
                await websocket.send(json.dumps(request))
                self.log_message(f"📤 Sent: {request}")

                # ノイズとして無視するタイプ
                NOISE_TYPES = {"connection", "ping", "heartbeat", "log", "server_info"}

                # 一覧レスポンス待ち（ノイズは捨てる）
                deadline = time.monotonic() + 5.0
                while True:
                    remain = deadline - time.monotonic()
                    if remain <= 0:
                        raise asyncio.TimeoutError()

                    raw = await asyncio.wait_for(websocket.recv(), timeout=remain)
                    self.log_message(f"📥 Received: {raw}")

                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        self.log_message("ℹ Ignored: non-JSON frame")
                        continue

                    t = data.get('type')

                    if t in ("client_list_response", "list_clients_response", "clients"):
                        self.clients = data.get('clients', [])
                        self.log_message(f"✓ Got {len(self.clients)} clients")
                        for i, client in enumerate(self.clients):
                            self.log_message(f"  Client {i+1}: {client}")

                        # ★ タイトル解決の追いリクエスト（可能なら）
                        await self._resolve_client_meta(websocket)

                        return True

                    if t in NOISE_TYPES:
                        self.log_message(f"ℹ Ignored: {t}")
                        continue

                    self.log_message(f"🔎 Side-event: {t}")

        except asyncio.TimeoutError:
            self.log_message("❌ Timeout waiting for server response")
            return False
        except websockets.exceptions.ConnectionRefused:
            self.log_message("❌ Connection refused - is the server running?")
            return False
        except Exception as e:
            self.log_message(f"❌ Connection error: {e}")
            return False


            
    def _update_client_list(self, success):
        """クライアント一覧を更新"""
        self.client_listbox.delete(0, tk.END)
        
        if success and self.clients:
            self.log_message(f"📋 Updating list with {len(self.clients)} clients")
            
            for i, client in enumerate(self.clients):
                live_title = client.get('live_title', 'No Title')
                live_id = client.get('live_id', 'Unknown')
                instance_id = client.get('instance_id', 'Unknown')
                connected_time = datetime.fromtimestamp(client.get('connected_at', 0)).strftime('%H:%M:%S')
                
                # 表示テキストを作成
                if live_title and live_title != 'No Title' and live_title != 'unknown':
                    display_text = f"{i+1:2}. {live_title[:40]}"
                    if len(live_title) > 40:
                        display_text += "..."
                else:
                    display_text = f"{i+1:2}. [No Title]"
                    
                display_text += f" | {live_id} | {connected_time}"
                
                self.client_listbox.insert(tk.END, display_text)
                self.log_message(f"   Added: {display_text}")
                
            self.log_message(f"✓ Client list updated successfully")
        elif success:
            self.client_listbox.insert(tk.END, "No clients connected")
            self.log_message("ℹ No NCV clients are connected")
        else:
            self.client_listbox.insert(tk.END, "Failed to connect to server")
            self.log_message("❌ Failed to get client list")
                
        self.refresh_button.config(state=tk.NORMAL, text="Refresh Clients")
        
    async def _resolve_client_meta(self, websocket):
        """
        live_title / live_id が unknown のクライアントに対して
        個別メタを問い合わせて上書きする。
        サーバー側に実装が無ければ静かに諦める。
        期待リクエスト: {"type":"get_client_info_request","instance_id": "..."}
        期待レスポンス: {"type":"get_client_info_response","instance_id":"...","live_id":"lv123","live_title":"..."}
        """
        # 未解決のみ対象
        unresolved = {c['instance_id']: c for c in self.clients
                      if (not c.get('live_title') or str(c.get('live_title')).lower() == 'unknown')}

        if not unresolved:
            return

        # 送信（まとめて投げる）
        for inst_id in list(unresolved.keys()):
            try:
                msg = {"type": "get_client_info_request", "instance_id": inst_id}
                await websocket.send(json.dumps(msg))
                self.log_message(f"📤 Meta request: {msg}")
            except Exception as e:
                self.log_message(f"⚠ Meta request failed ({inst_id}): {e}")

        # 受信ループ：最大2秒だけ待って、返ってきた分だけ上書き
        end = time.monotonic() + 2.0
        while unresolved and time.monotonic() < end:
            remain = max(0.05, end - time.monotonic())
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=remain)
            except asyncio.TimeoutError:
                break

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if data.get("type") != "get_client_info_response":
                continue

            inst_id = data.get("instance_id")
            if not inst_id or inst_id not in unresolved:
                continue

            # 上書き
            target = unresolved[inst_id]
            live_id = data.get("live_id") or target.get("live_id")
            live_title = data.get("live_title") or target.get("live_title")

            # “unknown” を実質的に None 扱いしてから上書き
            if isinstance(live_id, str) and live_id.lower() == "unknown":
                live_id = target.get("live_id")
            if isinstance(live_title, str) and live_title.lower() == "unknown":
                live_title = target.get("live_title")

            target["live_id"] = live_id
            target["live_title"] = live_title

            self.log_message(f"🧩 Resolved: {inst_id} -> title='{live_title}' id='{live_id}'")
            unresolved.pop(inst_id, None)

        if unresolved:
            self.log_message(f"ℹ Meta unresolved: {list(unresolved.keys())}")


    def on_client_select(self, event):
        """クライアント選択時の処理"""
        selection = self.client_listbox.curselection()
        if selection and self.clients:
            index = selection[0]
            if 0 <= index < len(self.clients):
                self.selected_client = self.clients[index]
                
                live_title = self.selected_client.get('live_title', 'No Title')
                live_id = self.selected_client.get('live_id', 'Unknown')
                
                self.selected_label.config(
                    text=f"Selected: {live_title} (ID: {live_id})", 
                    foreground="green"
                )
                self.set_comment_input_state(True)
                self.log_message(f"✓ Selected: {live_title}")
        else:
            self.selected_client = None
            self.selected_label.config(text="No client selected", foreground="red")
            self.set_comment_input_state(False)
            
    def set_comment_input_state(self, enabled):
        """コメント入力欄の有効/無効を切り替え"""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.comment_text.config(state=state)
        self.send_button.config(state=state)
        self.clear_button.config(state=state)
        
    def clear_comment(self):
        """コメント入力欄をクリア"""
        self.comment_text.delete("1.0", tk.END)
        
    def log_message(self, message):
        """ログメッセージを表示"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def send_comment(self):
        """コメント送信"""
        if not self.selected_client:
            messagebox.showwarning("Warning", "Please select a client first")
            return
            
        comment = self.comment_text.get("1.0", tk.END).strip()
        if not comment:
            messagebox.showwarning("Warning", "Please enter a comment")
            return
            
        self.send_button.config(state=tk.DISABLED, text="Sending...")
        
        # 別スレッドで送信
        thread = threading.Thread(target=self._send_comment_async, args=(comment,))
        thread.daemon = True
        thread.start()
        
    def _send_comment_async(self, comment):
        """非同期でコメント送信"""
        try:
            success = asyncio.run(self._send_to_server(comment))
            
            if success:
                client_title = self.selected_client.get('live_title', 'Unknown')
                self.root.after(0, lambda: self.log_message(f"✓ Sent to '{client_title}': {comment}"))
                self.root.after(0, self.clear_comment)
            else:
                self.root.after(0, lambda: self.log_message(f"❌ Failed to send: {comment}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Send error: {e}"))
        finally:
            self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL, text="Send Comment (Ctrl+Enter)"))
    
    async def _send_to_server(self, comment):
        """サーバーにコメント送信"""
        try:
            async with websockets.connect(self.server_uri, open_timeout=3) as websocket:
                message = {
                    'type': 'send_comment_to_specific_client',
                    'target_instance_id': self.selected_client['instance_id'],
                    'comment': comment,
                    'live_id': self.selected_client['live_id']
                }
                
                self.log_message(f"📤 Sending: {message}")
                await websocket.send(json.dumps(message))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                self.log_message(f"📥 Response: {response}")
                
                response_data = json.loads(response)
                return response_data.get('status') == 'success'
                
        except Exception as e:
            self.log_message(f"❌ Send connection error: {e}")
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = CommentSenderGUI(root)
    
    # ウィンドウを中央に配置
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass