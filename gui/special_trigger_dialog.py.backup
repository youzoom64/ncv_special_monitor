"""
スペシャルトリガー管理ダイアログ
"""
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as msgbox
import random

from .utils import log_to_gui


def should_trigger_fire(trigger_config):
    """トリガーが発火するかどうかを確率で判定"""
    probability = trigger_config.get("firing_probability", 100)
    probability = max(0, min(100, probability))
    random_value = random.randint(0, 99)
    return random_value < probability


class SpecialTriggerManagementDialog:
    def __init__(self, parent, config_manager, user_id):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("スペシャルトリガー管理")
        self.dialog.geometry("700x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()
        self.refresh_triggers_list()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 説明
        info_label = ttk.Label(main_frame, text="スペシャルトリガーは全ての設定を無視して最優先で発動します", font=("", 9))
        info_label.pack(anchor=tk.W, pady=(0, 10))

        # トリガー一覧
        list_frame = ttk.LabelFrame(main_frame, text="スペシャルトリガー一覧", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.triggers_tree = ttk.Treeview(
            list_frame,
            columns=("name", "enabled", "keywords", "condition"),
            show="tree headings",
            height=8
        )
        self.triggers_tree.heading("#0", text="選択")
        self.triggers_tree.heading("name", text="名前")
        self.triggers_tree.heading("enabled", text="状態")
        self.triggers_tree.heading("keywords", text="キーワード")
        self.triggers_tree.heading("condition", text="条件")

        self.triggers_tree.column("#0", width=60)
        self.triggers_tree.column("name", width=150)
        self.triggers_tree.column("enabled", width=60)
        self.triggers_tree.column("keywords", width=300)
        self.triggers_tree.column("condition", width=60)

        # チェックボックスクリック処理をバインド
        self.triggers_tree.bind("<Button-1>", self.on_trigger_click)

        self.triggers_tree.pack(fill=tk.BOTH, expand=True)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="追加", command=self.add_trigger).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="一括有効", command=self.enable_all_triggers).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="一括無効", command=self.disable_all_triggers).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="編集", command=self.edit_trigger).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="削除", command=self.delete_trigger).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="閉じる", command=self.close_dialog).pack(side=tk.RIGHT)

    def refresh_triggers_list(self):
        """トリガー一覧を更新"""
        for item in self.triggers_tree.get_children():
            self.triggers_tree.delete(item)

        triggers = self.config_manager.get_user_special_triggers(self.user_id)
        for trigger in triggers:
            name = trigger.get("name", "無名トリガー")
            enabled = trigger.get("enabled", True)
            keywords = ", ".join(trigger.get("keywords", []))
            condition = trigger.get("keyword_condition", "OR")

            # チェックボックス表示
            checkbox = "☑" if enabled else "☐"
            status = "有効" if enabled else "無効"

            self.triggers_tree.insert(
                "",
                tk.END,
                text=checkbox,
                values=(name, status, keywords, condition)
            )

    def add_trigger(self):
        """トリガー追加"""
        dialog = SpecialTriggerEditDialog(self.dialog, self.config_manager, self.user_id)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_triggers_list()

    def edit_trigger(self):
        """トリガー編集"""
        selected = self.triggers_tree.selection()
        if not selected:
            log_to_gui("編集するトリガーを選択してください")
            return

        selected_index = self.triggers_tree.index(selected[0])
        triggers = self.config_manager.get_user_special_triggers(self.user_id)

        if selected_index < len(triggers):
            trigger = triggers[selected_index]
            trigger_id = trigger.get("id")

            dialog = SpecialTriggerEditDialog(self.dialog, self.config_manager, self.user_id, trigger_id)
            self.dialog.wait_window(dialog.dialog)
            if dialog.result:
                self.refresh_triggers_list()

    def delete_trigger(self):
        """トリガー削除"""
        selected = self.triggers_tree.selection()
        if not selected:
            log_to_gui("削除するトリガーを選択してください")
            return

        selected_index = self.triggers_tree.index(selected[0])
        triggers = self.config_manager.get_user_special_triggers(self.user_id)

        if selected_index < len(triggers):
            trigger = triggers[selected_index]
            trigger_name = trigger.get("name", "無名トリガー")
            trigger_id = trigger.get("id")

            # 確認なしで削除
            if trigger_id:
                self.config_manager.delete_special_trigger_config(self.user_id, trigger_id)
                self.refresh_triggers_list()

    def on_trigger_click(self, event):
        """スペシャルトリガーのチェックボックスクリック処理"""
        item = self.triggers_tree.identify('item', event.x, event.y)
        column = self.triggers_tree.identify('column', event.x, event.y)

        # チェックボックス列（#0）がクリックされた場合
        if item and column == "#0":
            # 選択されたトリガーのインデックスを取得
            selected_index = self.triggers_tree.index(item)
            triggers = self.config_manager.get_user_special_triggers(self.user_id)

            if selected_index < len(triggers):
                trigger = triggers[selected_index]
                trigger_id = trigger.get("id")

                if trigger_id:
                    # 現在の状態を取得
                    current_text = self.triggers_tree.item(item, "text")
                    current_enabled = current_text == "☑"

                    # 状態を切り替え
                    new_enabled = not current_enabled
                    new_checkbox = "☑" if new_enabled else "☐"
                    new_status = "有効" if new_enabled else "無効"

                    # 表示を更新
                    self.triggers_tree.item(item, text=new_checkbox)
                    values = list(self.triggers_tree.item(item, "values"))
                    values[1] = new_status  # 状態列を更新
                    self.triggers_tree.item(item, values=values)

                    # 設定を保存
                    self.update_special_trigger_enabled_status(trigger_id, new_enabled)

    def update_special_trigger_enabled_status(self, trigger_id: str, enabled: bool):
        """スペシャルトリガーの有効/無効状態を更新"""
        try:
            triggers = self.config_manager.get_user_special_triggers(self.user_id)
            for trigger in triggers:
                if trigger.get("id") == trigger_id:
                    trigger["enabled"] = enabled
                    self.config_manager.save_special_trigger_config(self.user_id, trigger)

                    status_text = "有効" if enabled else "無効"
                    log_to_gui(f"スペシャルトリガー {trigger.get('name', '')} を{status_text}に変更しました")
                    break
        except Exception as e:
            msgbox.showerror("エラー", f"設定更新エラー: {str(e)}")

    def enable_all_triggers(self):
        """全スペシャルトリガーを一括有効化"""
        try:
            triggers = self.config_manager.get_user_special_triggers(self.user_id)
            updated_count = 0

            for trigger in triggers:
                if not trigger.get("enabled", True):
                    trigger["enabled"] = True
                    self.config_manager.save_special_trigger_config(self.user_id, trigger)
                    updated_count += 1

            self.refresh_triggers_list()
            log_to_gui(f"{updated_count}個のスペシャルトリガーを有効化しました")
        except Exception as e:
            log_to_gui(f"一括有効化エラー: {str(e)}")

    def disable_all_triggers(self):
        """全スペシャルトリガーを一括無効化"""
        triggers = self.config_manager.get_user_special_triggers(self.user_id)
        if not triggers:
            log_to_gui("トリガーが登録されていません")
            return

        try:
            updated_count = 0
            for trigger in triggers:
                if trigger.get("enabled", True):
                    trigger["enabled"] = False
                    self.config_manager.save_special_trigger_config(self.user_id, trigger)
                    updated_count += 1

            self.refresh_triggers_list()
            log_to_gui(f"{updated_count}個のスペシャルトリガーを無効化しました")
        except Exception as e:
            log_to_gui(f"一括無効化エラー: {str(e)}")

    def close_dialog(self):
        self.result = True
        self.dialog.destroy()


class SpecialTriggerEditDialog:
    def __init__(self, parent, config_manager, user_id, trigger_id=None):
        print(f"[GUI DEBUG] SpecialTriggerEditDialog.__init__ called:")
        print(f"[GUI DEBUG]   user_id: {user_id}")
        print(f"[GUI DEBUG]   trigger_id: {trigger_id}")
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.trigger_id = trigger_id

        if trigger_id:
            triggers = config_manager.get_user_special_triggers(user_id)
            self.trigger_config = next((t for t in triggers if t.get("id") == trigger_id), {})
        else:
            self.trigger_config = {
                "name": "新しいスペシャルトリガー",
                "enabled": True,
                "keywords": ["緊急"],
                "keyword_condition": "OR",
                "response_type": "predefined",
                "messages": [f">>{'{no}'} 🚨 スペシャルトリガー発動！"],
                "ai_response_prompt": "緊急事態として迅速に対応してください",
                "ignore_all_limits": True,
                "firing_probability": 100
            }

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("スペシャルトリガー編集" if trigger_id else "スペシャルトリガー追加")
        self.dialog.geometry("500x600")
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
        self.trigger_name_var = tk.StringVar(value=self.trigger_config.get("name", "新しいスペシャルトリガー"))
        ttk.Entry(basic_frame, textvariable=self.trigger_name_var).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        self.enabled_var = tk.BooleanVar(value=self.trigger_config.get("enabled", True))
        ttk.Checkbutton(basic_frame, text="有効", variable=self.enabled_var).grid(row=1, column=1, sticky=tk.W, padx=(5, 0))

        basic_frame.columnconfigure(1, weight=1)

        # キーワード設定
        keyword_frame = ttk.LabelFrame(main_frame, text="キーワード設定", padding="5")
        keyword_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(keyword_frame, text="キーワード (1行1キーワード):").pack(anchor=tk.W)
        self.keywords_text = tk.Text(keyword_frame, height=3)
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
        self.messages_text.pack
        self.messages_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        messages = self.trigger_config.get("messages", [])
        self.messages_text.insert("1.0", "\n".join(messages))

        ttk.Label(response_frame, text="AIプロンプト:").pack(anchor=tk.W)
        self.ai_prompt_var = tk.StringVar(value=self.trigger_config.get("ai_response_prompt", ""))
        ttk.Entry(response_frame, textvariable=self.ai_prompt_var).pack(fill=tk.X)

        # 確率設定
        probability_frame = ttk.LabelFrame(main_frame, text="発火設定", padding="5")
        probability_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(probability_frame, text="発火確率(%):").grid(row=0, column=0, sticky=tk.W)
        self.probability_var = tk.StringVar(value=str(self.trigger_config.get("firing_probability", 100)))
        ttk.Entry(probability_frame, textvariable=self.probability_var, width=10).grid(row=0, column=1, padx=(5, 0))
        ttk.Label(probability_frame, text="(0-100の数値で指定)").grid(row=0, column=2, padx=(5, 0), sticky=tk.W)

        # 注意事項
        note_frame = ttk.Frame(main_frame)
        note_frame.pack(fill=tk.X, pady=(0, 10))
        note_label = ttk.Label(note_frame, text="※ スペシャルトリガーは反応回数制限・クールダウン・遅延をすべて無視します",
                              font=("", 8), foreground="red")
        note_label.pack(anchor=tk.W)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_trigger).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

    def save_trigger(self):
        """トリガー保存"""
        print(f"[GUI DEBUG] SpecialTriggerEditDialog.save_trigger() method called")
        trigger_name = self.trigger_name_var.get().strip()
        print(f"[GUI DEBUG] special trigger_name: '{trigger_name}'")

        if not trigger_name:
            print(f"[GUI DEBUG] special trigger_name is empty, returning")
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
            messages = [f">>{'{no}'} 🚨 スペシャルトリガー発動！"]

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
            "ignore_all_limits": True,
            "firing_probability": int(self.probability_var.get() or 100)
        }

        self.config_manager.save_special_trigger_config(self.user_id, trigger_config)
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()