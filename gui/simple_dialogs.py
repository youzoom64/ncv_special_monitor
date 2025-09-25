"""
簡単なダイアログクラス群
"""
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as msgbox
import requests
from bs4 import BeautifulSoup

from .utils import log_to_gui


class SimpleBroadcasterEditDialog:
    """配信者追加用の簡単なダイアログ"""
    def __init__(self, parent, config_manager, user_id, broadcaster_id=None):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.broadcaster_id = broadcaster_id

        # 既存の配信者設定を取得（編集の場合）
        if broadcaster_id:
            user_config = config_manager.get_user_config(user_id)
            broadcasters = user_config.get("broadcasters", {})
            self.broadcaster_config = broadcasters.get(broadcaster_id, {})
            print(f"[GUI DEBUG] Loading broadcaster config for {broadcaster_id}: enabled={self.broadcaster_config.get('enabled', True)}")
        else:
            self.broadcaster_config = {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("配信者編集" if broadcaster_id else "配信者追加")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 基本情報
        ttk.Label(main_frame, text="配信者ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.broadcaster_id_var = tk.StringVar(value=self.broadcaster_config.get("broadcaster_id", ""))
        broadcaster_id_frame = ttk.Frame(main_frame)
        broadcaster_id_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)
        self.broadcaster_id_entry = ttk.Entry(broadcaster_id_frame, textvariable=self.broadcaster_id_var)
        self.broadcaster_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(broadcaster_id_frame, text="名前取得", command=self.fetch_broadcaster_name).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(main_frame, text="配信者名:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.broadcaster_name_var = tk.StringVar(value=self.broadcaster_config.get("broadcaster_name", ""))
        ttk.Entry(main_frame, textvariable=self.broadcaster_name_var, width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)

        current_enabled = self.broadcaster_config.get("enabled", True)
        print(f"[GUI DEBUG] SimpleBroadcasterEditDialog: Setting enabled checkbox to {current_enabled}")
        self.enabled_var = tk.BooleanVar(value=current_enabled)
        ttk.Checkbutton(main_frame, text="有効", variable=self.enabled_var).grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=5)

        # 最大反応回数
        ttk.Label(main_frame, text="最大反応回数:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.max_reactions_var = tk.IntVar(value=self.broadcaster_config.get("default_response", {}).get("max_reactions_per_stream", 1))
        ttk.Entry(main_frame, textvariable=self.max_reactions_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=(5, 0), pady=5)

        # 応答遅延
        ttk.Label(main_frame, text="応答遅延(秒):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.response_delay_var = tk.DoubleVar(value=self.broadcaster_config.get("default_response", {}).get("response_delay_seconds", 0))
        ttk.Entry(main_frame, textvariable=self.response_delay_var, width=10).grid(row=4, column=1, sticky=tk.W, padx=(5, 0), pady=5)

        # 分割送信間隔
        ttk.Label(main_frame, text="分割送信間隔(秒):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.split_delay_var = tk.DoubleVar(value=self.broadcaster_config.get("default_response", {}).get("response_split_delay_seconds", 1))
        ttk.Entry(main_frame, textvariable=self.split_delay_var, width=10).grid(row=5, column=1, sticky=tk.W, padx=(5, 0), pady=5)

        # 定型メッセージ
        ttk.Label(main_frame, text="定型メッセージ:").grid(row=6, column=0, sticky=tk.NW, pady=5)
        self.messages_text = tk.Text(main_frame, height=4, width=30)
        self.messages_text.grid(row=6, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0), pady=5)

        # デフォルトメッセージを設定
        default_messages = self.broadcaster_config.get("default_response", {}).get("messages", [])
        if default_messages:
            self.messages_text.insert("1.0", "\n".join(default_messages))
        else:
            broadcaster_name = self.broadcaster_config.get("broadcaster_name", "")
            if broadcaster_name:
                self.messages_text.insert("1.0", f">>{'{no}'} {broadcaster_name}での挨拶です")

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_broadcaster).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

    def save_broadcaster(self):
        """配信者保存"""
        broadcaster_id = self.broadcaster_id_var.get().strip()
        broadcaster_name = self.broadcaster_name_var.get().strip()
        enabled = self.enabled_var.get()

        print(f"[GUI DEBUG] SimpleBroadcasterEditDialog.save_broadcaster(): enabled={enabled}")

        if not broadcaster_id:
            log_to_gui("配信者IDを入力してください")
            return
        if not broadcaster_name:
            broadcaster_name = f"配信者{broadcaster_id}"

        # メッセージを処理
        messages_text = self.messages_text.get("1.0", tk.END).strip()
        messages = [msg.strip() for msg in messages_text.split("\n") if msg.strip()]
        if not messages:
            messages = [f">>{'{no}'} {broadcaster_name}での挨拶です"]

        # 汎用保存ロジックを使用
        def update_broadcaster(config):
            broadcasters = config.get("broadcasters", {})
            # 既存の配信者情報を保持しつつ更新
            if broadcaster_id in broadcasters:
                existing_broadcaster = broadcasters[broadcaster_id]
                existing_broadcaster.update({
                    "broadcaster_name": broadcaster_name,
                    "enabled": enabled,
                    "default_response": {
                        "response_type": "predefined",
                        "messages": messages,
                        "ai_response_prompt": f"{broadcaster_name}の配信に特化した親しみやすい返答をしてください",
                        "max_reactions_per_stream": self.max_reactions_var.get(),
                        "response_delay_seconds": self.response_delay_var.get(),
                        "response_split_delay_seconds": self.split_delay_var.get()
                    }
                })
            else:
                broadcasters[broadcaster_id] = {
                    "broadcaster_id": broadcaster_id,
                    "broadcaster_name": broadcaster_name,
                    "enabled": enabled,
                    "default_response": {
                        "response_type": "predefined",
                        "messages": messages,
                        "ai_response_prompt": f"{broadcaster_name}の配信に特化した親しみやすい返答をしてください",
                        "max_reactions_per_stream": self.max_reactions_var.get(),
                        "response_delay_seconds": self.response_delay_var.get(),
                        "response_split_delay_seconds": self.split_delay_var.get()
                    },
                    "triggers": []
                }
            config["broadcasters"] = broadcasters

        if self.config_manager._safe_save_user_config(self.user_id, update_broadcaster):
            print(f"[GUI DEBUG] SimpleBroadcasterEditDialog: Successfully saved broadcaster {broadcaster_id} with enabled={enabled}")
            self.result = True
            self.dialog.destroy()
        else:
            log_to_gui("配信者設定の保存に失敗しました")

    def cancel(self):
        self.dialog.destroy()

    def fetch_broadcaster_name(self):
        """配信者名取得"""
        broadcaster_id = self.broadcaster_id_var.get().strip()
        if not broadcaster_id:
            log_to_gui("配信者IDを入力してください")
            return

        try:
            url = f"https://www.nicovideo.jp/user/{broadcaster_id}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            # ユーザー名を取得
            nickname = None
            meta_tag = soup.find("meta", {"property": "profile:username"})
            if meta_tag and meta_tag.get("content"):
                nickname = meta_tag["content"]

            if nickname:
                self.broadcaster_name_var.set(nickname)
                log_to_gui(f"配信者名を取得しました: {nickname}")
            else:
                self.broadcaster_name_var.set(f"配信者{broadcaster_id}")
                log_to_gui("配信者名を取得できませんでした")

        except Exception as e:
            self.broadcaster_name_var.set(f"配信者{broadcaster_id}")
            log_to_gui(f"配信者情報の取得に失敗しました: {str(e)}")


class SimpleTriggerEditDialog:
    """トリガー追加用の簡単なダイアログ"""
    def __init__(self, parent, config_manager, user_id, broadcaster_id, broadcaster_name, trigger_index=None):
        print(f"[GUI DEBUG] SimpleTriggerEditDialog.__init__ called:")
        print(f"[GUI DEBUG]   user_id: {user_id}")
        print(f"[GUI DEBUG]   broadcaster_id: {broadcaster_id}")
        print(f"[GUI DEBUG]   broadcaster_name: {broadcaster_name}")
        print(f"[GUI DEBUG]   trigger_index: {trigger_index}")
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.broadcaster_id = broadcaster_id
        self.broadcaster_name = broadcaster_name
        self.trigger_index = trigger_index

        # 既存のトリガー設定を取得（編集の場合）
        if trigger_index is not None:
            user_config = config_manager.get_user_config(user_id)
            broadcasters = user_config.get("broadcasters", {})
            broadcaster_info = broadcasters.get(broadcaster_id, {})
            triggers = broadcaster_info.get("triggers", [])
            if 0 <= trigger_index < len(triggers):
                self.trigger_config = triggers[trigger_index]
            else:
                self.trigger_config = {}
        else:
            self.trigger_config = {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("トリガー編集" if trigger_index is not None else "トリガー追加")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 基本情報
        ttk.Label(main_frame, text="トリガー名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.trigger_name_var = tk.StringVar(value=self.trigger_config.get("name", ""))
        ttk.Entry(main_frame, textvariable=self.trigger_name_var, width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)

        self.enabled_var = tk.BooleanVar(value=self.trigger_config.get("enabled", True))
        ttk.Checkbutton(main_frame, text="有効", variable=self.enabled_var).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=5)

        # キーワード
        ttk.Label(main_frame, text="キーワード (1行1キーワード):").grid(row=2, column=0, sticky=tk.NW, pady=5)
        self.keywords_text = tk.Text(main_frame, height=4, width=40)
        self.keywords_text.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0), pady=5)
        keywords = self.trigger_config.get("keywords", [])
        if keywords:
            self.keywords_text.insert("1.0", "\n".join(keywords))

        # 応答タイプ
        ttk.Label(main_frame, text="応答タイプ:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.response_type_var = tk.StringVar(value=self.trigger_config.get("response_type", "predefined"))
        response_frame = ttk.Frame(main_frame)
        response_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)
        ttk.Radiobutton(response_frame, text="定型メッセージ", variable=self.response_type_var, value="predefined").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(response_frame, text="AI生成", variable=self.response_type_var, value="ai").pack(side=tk.LEFT)

        # メッセージ
        ttk.Label(main_frame, text="定型メッセージ (1行1メッセージ):").grid(row=4, column=0, sticky=tk.NW, pady=5)
        self.messages_text = tk.Text(main_frame, height=4, width=40)
        self.messages_text.grid(row=4, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0), pady=5)
        messages = self.trigger_config.get("messages", [])
        if messages:
            self.messages_text.insert("1.0", "\n".join(messages))

        # AIプロンプト
        ttk.Label(main_frame, text="AIプロンプト:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.ai_prompt_var = tk.StringVar(value=self.trigger_config.get("ai_response_prompt", ""))
        ttk.Entry(main_frame, textvariable=self.ai_prompt_var, width=40).grid(row=5, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)

        # 反応設定
        settings_frame = ttk.Frame(main_frame)
        settings_frame.grid(row=6, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)

        ttk.Label(settings_frame, text="最大反応回数:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.max_reactions_var = tk.IntVar(value=self.trigger_config.get("max_reactions_per_stream", 1))
        ttk.Entry(settings_frame, textvariable=self.max_reactions_var, width=8).grid(row=0, column=1, padx=(0, 10))

        ttk.Label(settings_frame, text="応答遅延(秒):").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.response_delay_var = tk.DoubleVar(value=self.trigger_config.get("response_delay_seconds", 0))
        ttk.Entry(settings_frame, textvariable=self.response_delay_var, width=8).grid(row=0, column=3, padx=(0, 10))

        ttk.Label(settings_frame, text="分割送信間隔(秒):").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.split_delay_var = tk.DoubleVar(value=self.trigger_config.get("response_split_delay_seconds", 1))
        ttk.Entry(settings_frame, textvariable=self.split_delay_var, width=8).grid(row=0, column=5)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_trigger).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

    def save_trigger(self):
        """トリガー保存"""
        print(f"[GUI DEBUG] SimpleTriggerEditDialog.save_trigger() method called")
        trigger_name = self.trigger_name_var.get().strip()
        print(f"[GUI DEBUG] simple trigger_name: '{trigger_name}'")
        if not trigger_name:
            print(f"[GUI DEBUG] simple trigger_name is empty, returning")
            log_to_gui("トリガー名を入力してください")
            return

        # キーワードを処理
        keywords_text = self.keywords_text.get("1.0", tk.END).strip()
        keywords = [kw.strip() for kw in keywords_text.split("\n") if kw.strip()]
        if not keywords:
            log_to_gui("少なくとも1つのキーワードを入力してください")
            return

        # メッセージを処理
        messages_text = self.messages_text.get("1.0", tk.END).strip()
        messages = [msg.strip() for msg in messages_text.split("\n") if msg.strip()]

        # トリガー設定を作成
        trigger_config = {
            "name": trigger_name,
            "enabled": self.enabled_var.get(),
            "keywords": keywords,
            "keyword_condition": "OR",
            "response_type": self.response_type_var.get(),
            "messages": messages,
            "ai_response_prompt": self.ai_prompt_var.get(),
            "max_reactions_per_stream": self.max_reactions_var.get(),
            "response_delay_seconds": self.response_delay_var.get(),
            "response_split_delay_seconds": self.split_delay_var.get(),
            "firing_probability": 100
        }

        # 新しいsave_trigger_configメソッドを使用
        print(f"[GUI DEBUG] Calling save_trigger_config...")
        print(f"[GUI DEBUG]   user_id: {self.user_id}")
        print(f"[GUI DEBUG]   broadcaster_id: {self.broadcaster_id}")
        print(f"[GUI DEBUG]   trigger_config: {trigger_config}")

        if self.trigger_index is not None:
            # 編集の場合: 既存のIDを保持
            triggers = self.config_manager.get_broadcaster_triggers(self.user_id, self.broadcaster_id)
            if 0 <= self.trigger_index < len(triggers):
                existing_trigger = triggers[self.trigger_index]
                trigger_config["id"] = existing_trigger.get("id")
                print(f"[GUI DEBUG] Editing existing trigger with ID: {trigger_config.get('id')}")

        self.config_manager.save_trigger_config(self.user_id, self.broadcaster_id, trigger_config)
        print(f"[GUI DEBUG] save_trigger_config call completed")

        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()