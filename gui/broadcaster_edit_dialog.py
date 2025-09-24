"""
配信者編集ダイアログ
"""
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as msgbox

from .utils import log_to_gui
from .trigger_dialog import TriggerManagementDialog
from .simple_dialogs import SimpleTriggerEditDialog


class BroadcasterEditDialog:
    def __init__(self, parent, config_manager, user_id, broadcaster_id=None):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.broadcaster_id = broadcaster_id

        if broadcaster_id:
            broadcasters = config_manager.get_user_broadcasters(user_id)
            self.broadcaster_config = broadcasters.get(broadcaster_id, config_manager.create_default_broadcaster_config(broadcaster_id))
        else:
            self.broadcaster_config = config_manager.create_default_broadcaster_config("")

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("配信者編集" if broadcaster_id else "配信者追加")
        self.dialog.geometry("1000x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左右分割
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # === 左側：配信者設定 ===
        # 基本情報
        basic_frame = ttk.LabelFrame(left_frame, text="基本情報", padding="5")
        basic_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(basic_frame, text="配信者ID:").grid(row=0, column=0, sticky=tk.W)
        self.broadcaster_id_var = tk.StringVar(value=self.broadcaster_config.get("broadcaster_id", ""))
        ttk.Entry(basic_frame, textvariable=self.broadcaster_id_var).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        ttk.Label(basic_frame, text="配信者名:").grid(row=1, column=0, sticky=tk.W)
        self.broadcaster_name_var = tk.StringVar(value=self.broadcaster_config.get("broadcaster_name", ""))
        ttk.Entry(basic_frame, textvariable=self.broadcaster_name_var).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        self.enabled_var = tk.BooleanVar(value=self.broadcaster_config.get("enabled", True))
        ttk.Checkbutton(basic_frame, text="有効", variable=self.enabled_var).grid(row=2, column=1, sticky=tk.W, padx=(5, 0))

        basic_frame.columnconfigure(1, weight=1)

        # デフォルト応答設定（配信者用）
        response_frame = ttk.LabelFrame(left_frame, text="この配信者でのデフォルト応答設定", padding="5")
        response_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 応答タイプ
        type_frame = ttk.Frame(response_frame)
        type_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(type_frame, text="応答タイプ:").pack(side=tk.LEFT)
        self.response_type_var = tk.StringVar(value=self.broadcaster_config.get("default_response", {}).get("response_type", "predefined"))
        ttk.Radiobutton(type_frame, text="定型メッセージ", variable=self.response_type_var, value="predefined").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(type_frame, text="AI生成", variable=self.response_type_var, value="ai").pack(side=tk.LEFT)

        # メッセージ設定
        ttk.Label(response_frame, text="定型メッセージ (1行1メッセージ):").pack(anchor=tk.W)
        self.messages_text = tk.Text(response_frame, height=4)
        self.messages_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        messages = self.broadcaster_config.get("default_response", {}).get("messages", [])
        self.messages_text.insert("1.0", "\n".join(messages))

        ttk.Label(response_frame, text="AIプロンプト:").pack(anchor=tk.W)
        self.ai_prompt_var = tk.StringVar(value=self.broadcaster_config.get("default_response", {}).get("ai_response_prompt", ""))
        ttk.Entry(response_frame, textvariable=self.ai_prompt_var).pack(fill=tk.X, pady=(0, 5))

        # 反応設定
        reaction_frame = ttk.Frame(response_frame)
        reaction_frame.pack(fill=tk.X)

        ttk.Label(reaction_frame, text="最大反応回数:").grid(row=0, column=0, sticky=tk.W)
        self.max_reactions_var = tk.StringVar(value=str(self.broadcaster_config.get("default_response", {}).get("max_reactions_per_stream", 1)))
        ttk.Entry(reaction_frame, textvariable=self.max_reactions_var, width=10).grid(row=0, column=1, padx=(5, 10))

        ttk.Label(reaction_frame, text="応答遅延(秒):").grid(row=0, column=2, sticky=tk.W)
        self.delay_var = tk.StringVar(value=str(self.broadcaster_config.get("default_response", {}).get("response_delay_seconds", 0)))
        ttk.Entry(reaction_frame, textvariable=self.delay_var, width=10).grid(row=0, column=3, padx=(5, 0))

        # ボタン
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_broadcaster).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

        # === 右側：トリガー一覧 ===
        triggers_frame = ttk.LabelFrame(right_frame, text="この配信者のトリガー一覧", padding="5")
        triggers_frame.pack(fill=tk.BOTH, expand=True)

        # トリガー一覧Treeview
        self.triggers_tree = ttk.Treeview(
            triggers_frame,
            columns=("trigger_name", "enabled", "keywords", "response_type"),
            show="tree headings",
            height=15
        )
        self.triggers_tree.heading("#0", text="有効")
        self.triggers_tree.heading("trigger_name", text="トリガー名")
        self.triggers_tree.heading("enabled", text="状態")
        self.triggers_tree.heading("keywords", text="キーワード")
        self.triggers_tree.heading("response_type", text="応答タイプ")

        self.triggers_tree.column("#0", width=60)
        self.triggers_tree.column("trigger_name", width=120)
        self.triggers_tree.column("enabled", width=50)
        self.triggers_tree.column("keywords", width=100)
        self.triggers_tree.column("response_type", width=80)

        self.triggers_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # ダブルクリックでトリガー管理画面へ
        self.triggers_tree.bind("<Double-1>", self.on_trigger_double_click)
        # チェックボックスクリックイベント
        self.triggers_tree.bind("<Button-1>", self.on_trigger_click)

        # トリガー操作ボタン
        trigger_button_frame = ttk.Frame(triggers_frame)
        trigger_button_frame.pack(fill=tk.X)

        ttk.Button(trigger_button_frame, text="トリガー追加", command=self.add_trigger).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(trigger_button_frame, text="削除", command=self.delete_trigger).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(trigger_button_frame, text="一括有効", command=self.enable_all_triggers).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(trigger_button_frame, text="一括無効", command=self.disable_all_triggers).pack(side=tk.LEFT, padx=(2, 0))

        # トリガー一覧を初期表示
        self.refresh_triggers_list()

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
                "response_type": self.response_type_var.get(),
                "messages": messages,
                "ai_response_prompt": self.ai_prompt_var.get(),
                "max_reactions_per_stream": int(self.max_reactions_var.get() or 1),
                "response_delay_seconds": int(self.delay_var.get() or 0)
            },
            "triggers": self.broadcaster_config.get("triggers", [])
        }

        self.config_manager.save_broadcaster_config(self.user_id, broadcaster_id, broadcaster_config)
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()

    def refresh_triggers_list(self):
        """トリガー一覧を更新"""
        # 既存の項目をクリア
        for item in self.triggers_tree.get_children():
            self.triggers_tree.delete(item)

        # 配信者IDが設定されていない場合は何も表示しない
        broadcaster_id = self.broadcaster_id or self.broadcaster_id_var.get().strip()
        if not broadcaster_id:
            return

        # 現在の配信者のトリガーを取得
        user_config = self.config_manager.get_user_config(self.user_id)
        broadcasters = user_config.get("broadcasters", {})
        broadcaster_info = broadcasters.get(broadcaster_id, {})
        triggers = broadcaster_info.get("triggers", [])

        # トリガー一覧を表示
        for trigger in triggers:
            trigger_name = trigger.get("name", "無名トリガー")
            enabled = trigger.get("enabled", True)
            status = "有効" if enabled else "無効"
            checkbox = "☑" if enabled else "☐"
            keywords = ", ".join(trigger.get("keywords", [])[:3])  # 最初の3つのキーワードを表示
            if len(trigger.get("keywords", [])) > 3:
                keywords += "..."
            response_type_map = {"predefined": "定型", "ai": "AI"}
            response_type = response_type_map.get(trigger.get("response_type", "predefined"), "定型")

            self.triggers_tree.insert(
                "",
                tk.END,
                text=checkbox,
                values=(trigger_name, status, keywords, response_type)
            )

    def on_trigger_double_click(self, event):
        """トリガーダブルクリック処理"""
        selection = self.triggers_tree.selection()
        if not selection:
            return

        # 配信者IDを取得
        broadcaster_id = self.broadcaster_id or self.broadcaster_id_var.get().strip()
        if not broadcaster_id:
            log_to_gui("配信者IDが設定されていません")
            return

        # 配信者名を取得
        broadcaster_name = self.broadcaster_name_var.get().strip() or f"配信者{broadcaster_id}"

        # トリガー管理ダイアログを開く
        dialog = TriggerManagementDialog(self.dialog, self.config_manager, self.user_id, broadcaster_id, broadcaster_name)
        self.dialog.wait_window(dialog.dialog)

        # ダイアログが閉じられた後、トリガー一覧を更新
        self.refresh_triggers_list()

    def add_trigger(self):
        """トリガー追加"""
        broadcaster_id = self.broadcaster_id or self.broadcaster_id_var.get().strip()
        if not broadcaster_id:
            log_to_gui("配信者IDが設定されていません")
            return

        broadcaster_name = self.broadcaster_name_var.get().strip() or f"配信者{broadcaster_id}"

        # 簡単なトリガー追加ダイアログ
        dialog = SimpleTriggerEditDialog(self.dialog, self.config_manager, self.user_id, broadcaster_id, broadcaster_name)
        self.dialog.wait_window(dialog.dialog)

        if dialog.result:
            self.refresh_triggers_list()

    def delete_trigger(self):
        """トリガー削除"""
        selection = self.triggers_tree.selection()
        if not selection:
            log_to_gui("削除するトリガーを選択してください")
            return

        broadcaster_id = self.broadcaster_id or self.broadcaster_id_var.get().strip()
        if not broadcaster_id:
            log_to_gui("配信者IDが設定されていません")
            return

        # 選択されたトリガーの情報を取得
        item_values = self.triggers_tree.item(selection[0], "values")
        trigger_name = item_values[0]

        # 確認ダイアログ
        if msgbox.askyesno("確認", f"トリガー '{trigger_name}' を削除しますか？"):
            user_config = self.config_manager.get_user_config(self.user_id)
            broadcasters = user_config.get("broadcasters", {})
            if broadcaster_id in broadcasters:
                triggers = broadcasters[broadcaster_id].get("triggers", [])
                # 名前でトリガーを検索して削除
                updated_triggers = [t for t in triggers if t.get("name", "") != trigger_name]
                broadcasters[broadcaster_id]["triggers"] = updated_triggers
                user_config["broadcasters"] = broadcasters
                self.config_manager.save_user_config(self.user_id, user_config)
                self.refresh_triggers_list()
                log_to_gui(f"トリガー '{trigger_name}' を削除しました")

    def on_trigger_click(self, event):
        """トリガーのチェックボックスクリック処理"""
        item = self.triggers_tree.identify('item', event.x, event.y)
        column = self.triggers_tree.identify('column', event.x, event.y)

        # チェックボックス列（#0）がクリックされた場合
        if item and column == "#0":
            broadcaster_id = self.broadcaster_id or self.broadcaster_id_var.get().strip()
            if not broadcaster_id:
                log_to_gui("配信者IDが設定されていません")
                return

            # 選択されたトリガーの情報を取得
            item_values = self.triggers_tree.item(item, "values")
            trigger_name = item_values[0]

            # 現在の状態を取得し、切り替える
            user_config = self.config_manager.get_user_config(self.user_id)
            broadcasters = user_config.get("broadcasters", {})
            if broadcaster_id in broadcasters:
                triggers = broadcasters[broadcaster_id].get("triggers", [])
                # 名前でトリガーを検索して有効/無効を切り替える
                for trigger in triggers:
                    if trigger.get("name", "") == trigger_name:
                        current_enabled = trigger.get("enabled", True)
                        new_enabled = not current_enabled
                        trigger["enabled"] = new_enabled
                        break

                broadcasters[broadcaster_id]["triggers"] = triggers
                user_config["broadcasters"] = broadcasters
                self.config_manager.save_user_config(self.user_id, user_config)
                self.refresh_triggers_list()
                action = "有効" if new_enabled else "無効"
                log_to_gui(f"トリガー '{trigger_name}' を{action}にしました")

    def enable_all_triggers(self):
        """すべてのトリガーを有効化"""
        self._toggle_all_triggers_enabled(True)

    def disable_all_triggers(self):
        """すべてのトリガーを無効化"""
        self._toggle_all_triggers_enabled(False)

    def _toggle_all_triggers_enabled(self, enabled):
        """すべてのトリガーの有効/無効を切り替え"""
        broadcaster_id = self.broadcaster_id or self.broadcaster_id_var.get().strip()
        if not broadcaster_id:
            log_to_gui("配信者IDが設定されていません")
            return

        user_config = self.config_manager.get_user_config(self.user_id)
        broadcasters = user_config.get("broadcasters", {})

        if broadcaster_id not in broadcasters:
            log_to_gui("配信者が見つかりません")
            return

        triggers = broadcasters[broadcaster_id].get("triggers", [])
        if not triggers:
            log_to_gui("トリガーが設定されていません")
            return

        # すべてのトリガーの設定を更新
        for trigger in triggers:
            trigger["enabled"] = enabled

        broadcasters[broadcaster_id]["triggers"] = triggers
        user_config["broadcasters"] = broadcasters
        self.config_manager.save_user_config(self.user_id, user_config)
        self.refresh_triggers_list()
        action = "有効" if enabled else "無効"
        log_to_gui(f"すべてのトリガーを{action}にしました")