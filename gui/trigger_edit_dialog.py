"""
トリガー編集ダイアログ
"""
import tkinter as tk
from tkinter import ttk

from .utils import log_to_gui


class TriggerEditDialog:
    def __init__(self, parent, config_manager, user_id, broadcaster_id, trigger_id=None):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.broadcaster_id = broadcaster_id
        self.trigger_id = trigger_id

        if trigger_id:
            triggers = config_manager.get_broadcaster_triggers(user_id, broadcaster_id)
            self.trigger_config = next((t for t in triggers if t.get("id") == trigger_id), config_manager.create_default_trigger_config())
        else:
            self.trigger_config = config_manager.create_default_trigger_config()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("トリガー編集" if trigger_id else "トリガー追加")
        self.dialog.geometry("600x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 基本情報
        basic_frame = ttk.LabelFrame(main_frame, text="基本情報", padding="5")
        basic_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(basic_frame, text="トリガー名:").grid(row=0, column=0, sticky=tk.W)
        self.trigger_name_var = tk.StringVar(value=self.trigger_config.get("name", "新しいトリガー"))
        ttk.Entry(basic_frame, textvariable=self.trigger_name_var).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        self.enabled_var = tk.BooleanVar(value=self.trigger_config.get("enabled", True))
        ttk.Checkbutton(basic_frame, text="有効", variable=self.enabled_var).grid(row=1, column=1, sticky=tk.W, padx=(5, 0))

        basic_frame.columnconfigure(1, weight=1)

        # キーワード設定
        keyword_frame = ttk.LabelFrame(main_frame, text="キーワード設定", padding="5")
        keyword_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(keyword_frame, text="キーワード (1行1キーワード):").pack(anchor=tk.W)
        self.keywords_text = tk.Text(keyword_frame, height=4)
        self.keywords_text.pack(fill=tk.X, pady=(0, 5))
        keywords = self.trigger_config.get("keywords", [])
        self.keywords_text.insert("1.0", "\n".join(keywords))

        condition_frame = ttk.Frame(keyword_frame)
        condition_frame.pack(fill=tk.X)
        ttk.Label(condition_frame, text="条件:").pack(side=tk.LEFT)
        self.keyword_condition_var = tk.StringVar(value=self.trigger_config.get("keyword_condition", "OR"))
        ttk.Radiobutton(condition_frame, text="OR (いずれか)", variable=self.keyword_condition_var, value="OR").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(condition_frame, text="AND (すべて)", variable=self.keyword_condition_var, value="AND").pack(side=tk.LEFT)

        # 応答設定
        response_frame = ttk.LabelFrame(main_frame, text="応答設定", padding="5")
        response_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 応答タイプ
        type_frame = ttk.Frame(response_frame)
        type_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(type_frame, text="応答タイプ:").pack(side=tk.LEFT)
        self.response_type_var = tk.StringVar(value=self.trigger_config.get("response_type", "predefined"))
        ttk.Radiobutton(type_frame, text="定型メッセージ", variable=self.response_type_var, value="predefined").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(type_frame, text="AI生成", variable=self.response_type_var, value="ai").pack(side=tk.LEFT)

        # メッセージ設定
        ttk.Label(response_frame, text="定型メッセージ (1行1メッセージ):").pack(anchor=tk.W)
        self.messages_text = tk.Text(response_frame, height=4)
        self.messages_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        messages = self.trigger_config.get("messages", [])
        self.messages_text.insert("1.0", "\n".join(messages))

        ttk.Label(response_frame, text="AIプロンプト:").pack(anchor=tk.W)
        self.ai_prompt_var = tk.StringVar(value=self.trigger_config.get("ai_response_prompt", ""))
        ttk.Entry(response_frame, textvariable=self.ai_prompt_var).pack(fill=tk.X, pady=(0, 5))

        # 詳細設定
        detail_frame = ttk.Frame(response_frame)
        detail_frame.pack(fill=tk.X)

        ttk.Label(detail_frame, text="最大反応回数:").grid(row=0, column=0, sticky=tk.W)
        self.max_reactions_var = tk.StringVar(value=str(self.trigger_config.get("max_reactions_per_stream", 1)))
        ttk.Entry(detail_frame, textvariable=self.max_reactions_var, width=10).grid(row=0, column=1, padx=(5, 10))

        ttk.Label(detail_frame, text="応答遅延(秒):").grid(row=0, column=2, sticky=tk.W)
        self.delay_var = tk.StringVar(value=str(self.trigger_config.get("response_delay_seconds", 0)))
        ttk.Entry(detail_frame, textvariable=self.delay_var, width=10).grid(row=0, column=3, padx=(5, 10))

        ttk.Label(detail_frame, text="クールダウン(分):").grid(row=0, column=4, sticky=tk.W)
        self.cooldown_var = tk.StringVar(value=str(self.trigger_config.get("cooldown_minutes", 30)))
        ttk.Entry(detail_frame, textvariable=self.cooldown_var, width=10).grid(row=0, column=5, padx=(5, 10))

        ttk.Label(detail_frame, text="発火確率(%):").grid(row=1, column=0, sticky=tk.W)
        self.probability_var = tk.StringVar(value=str(self.trigger_config.get("firing_probability", 100)))
        ttk.Entry(detail_frame, textvariable=self.probability_var, width=10).grid(row=1, column=1, padx=(5, 0))

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

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
            log_to_gui("キーワードを少なくとも1つ入力してください")
            return

        # メッセージを処理
        messages_text = self.messages_text.get("1.0", tk.END).strip()
        messages = [msg.strip() for msg in messages_text.split("\n") if msg.strip()]
        if not messages:
            messages = [f">>{'{no}'} こんにちは！"]

        # 設定を作成
        trigger_config = {
            "id": self.trigger_config.get("id"),  # 既存の場合はIDを保持
            "name": trigger_name,
            "enabled": self.enabled_var.get(),
            "keywords": keywords,
            "keyword_condition": self.keyword_condition_var.get(),
            "response_type": self.response_type_var.get(),
            "messages": messages,
            "ai_response_prompt": self.ai_prompt_var.get(),
            "max_reactions_per_stream": int(self.max_reactions_var.get() or 1),
            "response_delay_seconds": int(self.delay_var.get() or 0),
            "cooldown_minutes": int(self.cooldown_var.get() or 30),
            "firing_probability": int(self.probability_var.get() or 100)
        }

        self.config_manager.save_trigger_config(self.user_id, self.broadcaster_id, trigger_config)
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()