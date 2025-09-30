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
        self.dialog.geometry("700x550")  # 縦を長くして下部ボタンが見えるように
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
        # ダブルクリックで編集画面へ移動
        self.triggers_tree.bind("<Double-1>", self.on_trigger_double_click)

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

    def on_trigger_double_click(self, event):
        """トリガーダブルクリック処理"""
        # ダブルクリックされた項目と列を取得
        item = self.triggers_tree.identify('item', event.x, event.y)
        column = self.triggers_tree.identify('column', event.x, event.y)

        if not item:
            return

        # チェックボックス列（#0）のダブルクリックは無視
        if column == "#0":
            return

        # 選択されたトリガーの情報を取得
        selected_index = self.triggers_tree.index(item)
        triggers = self.config_manager.get_user_special_triggers(self.user_id)

        print(f"[DEBUG] Double-click: selected_index={selected_index}, triggers count={len(triggers)}")

        if selected_index < len(triggers):
            trigger = triggers[selected_index]
            trigger_id = trigger.get("id")
            trigger_name = trigger.get("name", "無名")

            print(f"[DEBUG] Trigger: name={trigger_name}, id={trigger_id}")

            # 編集ダイアログを開く（trigger_indexを渡す）
            dialog = SpecialTriggerEditDialog(
                self.dialog,
                self.config_manager,
                self.user_id,
                trigger_id=trigger_id,
                trigger_index=selected_index
            )
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

            if msgbox.askyesno("確認", f"トリガー '{trigger_name}' を削除しますか？"):
                self.config_manager.delete_special_trigger_config(self.user_id, trigger_id)
                self.refresh_triggers_list()
                log_to_gui(f"トリガー '{trigger_name}' を削除しました")

    def enable_all_triggers(self):
        """全てのトリガーを有効化"""
        triggers = self.config_manager.get_user_special_triggers(self.user_id)
        for trigger in triggers:
            trigger["enabled"] = True
            self.config_manager.save_special_trigger_config(self.user_id, trigger)
        self.refresh_triggers_list()
        log_to_gui("全てのスペシャルトリガーを有効にしました")

    def disable_all_triggers(self):
        """全てのトリガーを無効化"""
        triggers = self.config_manager.get_user_special_triggers(self.user_id)
        for trigger in triggers:
            trigger["enabled"] = False
            self.config_manager.save_special_trigger_config(self.user_id, trigger)
        self.refresh_triggers_list()
        log_to_gui("全てのスペシャルトリガーを無効にしました")

    def on_trigger_click(self, event):
        """トリガーのチェックボックスクリック処理"""
        item = self.triggers_tree.identify('item', event.x, event.y)
        column = self.triggers_tree.identify('column', event.x, event.y)

        # チェックボックス列（#0）がクリックされた場合
        if item and column == "#0":
            selected_index = self.triggers_tree.index(item)
            triggers = self.config_manager.get_user_special_triggers(self.user_id)

            if selected_index < len(triggers):
                trigger = triggers[selected_index]
                current_enabled = trigger.get("enabled", True)
                new_enabled = not current_enabled

                trigger["enabled"] = new_enabled
                self.config_manager.save_special_trigger_config(self.user_id, trigger)
                self.refresh_triggers_list()

                action = "有効" if new_enabled else "無効"
                trigger_name = trigger.get("name", "無名トリガー")
                log_to_gui(f"トリガー '{trigger_name}' を{action}にしました")

    def close_dialog(self):
        """ダイアログを閉じる"""
        self.result = True
        self.dialog.destroy()


class SpecialTriggerEditDialog:
    def __init__(self, parent, config_manager, user_id, trigger_id=None, trigger_index=None):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.trigger_id = trigger_id
        self.trigger_index = trigger_index

        # 既存のトリガーがある場合は読み込み
        self.trigger_config = {}
        triggers = config_manager.get_user_special_triggers(user_id)

        # trigger_indexが指定されている場合はインデックスで取得
        if trigger_index is not None and 0 <= trigger_index < len(triggers):
            self.trigger_config = triggers[trigger_index].copy()
            if self.trigger_config.get("id") is None:
                self.trigger_id = None  # idがNoneの場合
        # trigger_idが指定されている場合はIDで検索
        elif trigger_id:
            for trigger in triggers:
                if trigger.get("id") == trigger_id:
                    self.trigger_config = trigger.copy()
                    break

        # 編集モードかどうかを判定（設定が読み込まれていれば編集モード）
        is_edit_mode = bool(self.trigger_config)

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("スペシャルトリガー編集" if is_edit_mode else "スペシャルトリガー追加")
        self.dialog.geometry("500x550")  # 縦を長くして下部ボタンが見えるように
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 基本設定
        basic_frame = ttk.LabelFrame(main_frame, text="基本設定", padding="5")
        basic_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(basic_frame, text="名前:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.name_var = tk.StringVar(value=self.trigger_config.get("name", ""))
        ttk.Entry(basic_frame, textvariable=self.name_var).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)

        self.enabled_var = tk.BooleanVar(value=self.trigger_config.get("enabled", True))
        ttk.Checkbutton(basic_frame, text="有効", variable=self.enabled_var).grid(row=1, column=1, sticky=tk.W, pady=2)

        basic_frame.columnconfigure(1, weight=1)

        # キーワード設定
        keyword_frame = ttk.LabelFrame(main_frame, text="キーワード設定", padding="5")
        keyword_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(keyword_frame, text="キーワード (1行1キーワード):").pack(anchor=tk.W)
        self.keywords_text = tk.Text(keyword_frame, height=5)
        self.keywords_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        keywords = self.trigger_config.get("keywords", [])
        self.keywords_text.insert("1.0", "\n".join(keywords))

        condition_frame = ttk.Frame(keyword_frame)
        condition_frame.pack(fill=tk.X)

        ttk.Label(condition_frame, text="条件:").pack(side=tk.LEFT)
        self.condition_var = tk.StringVar(value=self.trigger_config.get("keyword_condition", "OR"))
        ttk.Radiobutton(condition_frame, text="OR (いずれか)", variable=self.condition_var, value="OR").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(condition_frame, text="AND (すべて)", variable=self.condition_var, value="AND").pack(side=tk.LEFT)

        # 応答設定
        response_frame = ttk.LabelFrame(main_frame, text="応答設定", padding="5")
        response_frame.pack(fill=tk.X, pady=(0, 10))

        type_frame = ttk.Frame(response_frame)
        type_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(type_frame, text="応答タイプ:").pack(side=tk.LEFT)
        self.response_type_var = tk.StringVar(value=self.trigger_config.get("response_type", "predefined"))
        ttk.Radiobutton(type_frame, text="定型メッセージ", variable=self.response_type_var, value="predefined").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(type_frame, text="AI生成", variable=self.response_type_var, value="ai").pack(side=tk.LEFT)

        ttk.Label(response_frame, text="定型メッセージ (1行1メッセージ):").pack(anchor=tk.W)
        self.messages_text = tk.Text(response_frame, height=3)
        self.messages_text.pack(fill=tk.X, pady=(0, 5))
        messages = self.trigger_config.get("messages", [])
        self.messages_text.insert("1.0", "\n".join(messages))

        ttk.Label(response_frame, text="AIプロンプト:").pack(anchor=tk.W)
        self.ai_prompt_var = tk.StringVar(value=self.trigger_config.get("ai_response_prompt", ""))
        ttk.Entry(response_frame, textvariable=self.ai_prompt_var).pack(fill=tk.X, pady=2)

        # 詳細設定
        detail_frame = ttk.LabelFrame(main_frame, text="詳細設定", padding="5")
        detail_frame.pack(fill=tk.X, pady=(0, 10))

        settings_grid = ttk.Frame(detail_frame)
        settings_grid.pack(fill=tk.X)

        ttk.Label(settings_grid, text="発動確率(%):").grid(row=0, column=0, sticky=tk.W)
        self.probability_var = tk.StringVar(value=str(self.trigger_config.get("firing_probability", 100)))
        ttk.Entry(settings_grid, textvariable=self.probability_var, width=10).grid(row=0, column=1, padx=(5, 10))

        self.ignore_limits_var = tk.BooleanVar(value=self.trigger_config.get("ignore_all_limits", True))
        ttk.Checkbutton(settings_grid, text="全制限を無視", variable=self.ignore_limits_var).grid(row=0, column=2, sticky=tk.W)

        # 外部プログラム実行設定
        exec_frame = ttk.LabelFrame(main_frame, text="外部プログラム実行", padding="5")
        exec_frame.pack(fill=tk.X, pady=(0, 10))

        self.execute_program_var = tk.BooleanVar(value=self.trigger_config.get("execute_program", False))
        ttk.Checkbutton(exec_frame, text="外部プログラムを実行", variable=self.execute_program_var).pack(anchor=tk.W)

        ttk.Label(exec_frame, text="プログラムパス (.exe, .bat):").pack(anchor=tk.W, pady=(5, 0))

        path_frame = ttk.Frame(exec_frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))

        self.program_path_var = tk.StringVar(value=self.trigger_config.get("program_path", ""))
        ttk.Entry(path_frame, textvariable=self.program_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="参照", command=self.browse_program).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(exec_frame, text="引数（オプション）:").pack(anchor=tk.W)
        self.program_args_var = tk.StringVar(value=self.trigger_config.get("program_args", ""))
        ttk.Entry(exec_frame, textvariable=self.program_args_var).pack(fill=tk.X, pady=(0, 2))

        help_text = ttk.Label(exec_frame, text="変数: {user_name}, {user_id}, {comment}, {live_id}", font=("", 8), foreground="gray")
        help_text.pack(anchor=tk.W)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_trigger).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

    def save_trigger(self):
        """トリガー保存"""
        name = self.name_var.get().strip()
        if not name:
            log_to_gui("名前を入力してください")
            return

        keywords_text = self.keywords_text.get("1.0", tk.END).strip()
        keywords = [kw.strip() for kw in keywords_text.split("\n") if kw.strip()]
        if not keywords:
            log_to_gui("キーワードを入力してください")
            return

        messages_text = self.messages_text.get("1.0", tk.END).strip()
        messages = [msg.strip() for msg in messages_text.split("\n") if msg.strip()]

        trigger_config = {
            "id": self.trigger_id,
            "name": name,
            "enabled": self.enabled_var.get(),
            "keywords": keywords,
            "keyword_condition": self.condition_var.get(),
            "response_type": self.response_type_var.get(),
            "messages": messages,
            "ai_response_prompt": self.ai_prompt_var.get(),
            "ignore_all_limits": self.ignore_limits_var.get(),
            "firing_probability": int(self.probability_var.get() or 100)
        }

        self.config_manager.save_special_trigger_config(self.user_id, trigger_config)
        log_to_gui(f"スペシャルトリガー '{name}' を保存しました")
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        """キャンセル"""
        self.dialog.destroy()