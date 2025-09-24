"""
簡単なダイアログクラス群
"""
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as msgbox

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
        ttk.Entry(main_frame, textvariable=self.broadcaster_id_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)

        ttk.Label(main_frame, text="配信者名:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.broadcaster_name_var = tk.StringVar(value=self.broadcaster_config.get("broadcaster_name", ""))
        ttk.Entry(main_frame, textvariable=self.broadcaster_name_var, width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)

        self.enabled_var = tk.BooleanVar(value=self.broadcaster_config.get("enabled", True))
        ttk.Checkbutton(main_frame, text="有効", variable=self.enabled_var).grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=5)

        # 定型メッセージ
        ttk.Label(main_frame, text="定型メッセージ:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.messages_text = tk.Text(main_frame, height=4, width=30)
        self.messages_text.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0), pady=5)

        # デフォルトメッセージを設定
        default_messages = self.broadcaster_config.get("default_response", {}).get("messages", [])
        if default_messages:
            self.messages_text.insert("1.0", "\n".join(default_messages))
        else:
            broadcaster_name = self.broadcaster_config.get("broadcaster_name", "")
            if broadcaster_name:
                self.messages_text.insert("1.0", f">>{'{no}'} {broadcaster_name}での挨拶です")

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_broadcaster).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

    def save_broadcaster(self):
        """配信者保存"""
        broadcaster_id = self.broadcaster_id_var.get().strip()
        broadcaster_name = self.broadcaster_name_var.get().strip()

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

        # 設定を作成
        broadcaster_config = {
            "broadcaster_id": broadcaster_id,
            "broadcaster_name": broadcaster_name,
            "enabled": self.enabled_var.get(),
            "default_response": {
                "response_type": "predefined",
                "messages": messages,
                "ai_response_prompt": f"{broadcaster_name}の配信に特化した親しみやすい返答をしてください",
                "max_reactions_per_stream": 1,
                "response_delay_seconds": 0
            },
            "triggers": self.broadcaster_config.get("triggers", [])
        }

        self.config_manager.save_broadcaster_config(self.user_id, broadcaster_id, broadcaster_config)
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()


class SimpleTriggerEditDialog:
    """トリガー追加用の簡単なダイアログ"""
    def __init__(self, parent, config_manager, user_id, broadcaster_id, broadcaster_name, trigger_index=None):
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

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_trigger).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

    def save_trigger(self):
        """トリガー保存"""
        trigger_name = self.trigger_name_var.get().strip()
        if not trigger_name:
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
            "max_reactions_per_stream": 1,
            "response_delay_seconds": 0,
            "firing_probability": 100
        }

        # 配信者の設定を更新
        user_config = self.config_manager.get_user_config(self.user_id)
        broadcasters = user_config.get("broadcasters", {})

        if self.broadcaster_id not in broadcasters:
            log_to_gui("配信者が見つかりません")
            return

        triggers = broadcasters[self.broadcaster_id].get("triggers", [])

        if self.trigger_index is not None:
            # 編集の場合
            if 0 <= self.trigger_index < len(triggers):
                triggers[self.trigger_index] = trigger_config
        else:
            # 新規追加の場合
            triggers.append(trigger_config)

        broadcasters[self.broadcaster_id]["triggers"] = triggers
        user_config["broadcasters"] = broadcasters
        self.config_manager.save_user_config(self.user_id, user_config)

        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()