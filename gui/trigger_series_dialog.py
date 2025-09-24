"""
トリガーシリーズ管理ダイアログ
"""
import tkinter as tk
from tkinter import ttk, messagebox
import uuid


class TriggerSeriesManagementDialog:
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None

        # ダイアログ作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("トリガーシリーズ管理")
        self.dialog.geometry("900x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # ダイアログを中央に配置
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"900x600+{x}+{y}")

        self.setup_ui()
        self.load_series_list()

    def setup_ui(self):
        """UI設定"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左右分割
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # 左側：シリーズ一覧
        series_label = ttk.Label(left_frame, text="トリガーシリーズ一覧", font=("", 12, "bold"))
        series_label.pack(anchor=tk.W, pady=(0, 10))

        # シリーズリストのフレーム
        series_list_frame = ttk.Frame(left_frame)
        series_list_frame.pack(fill=tk.BOTH, expand=True)

        # シリーズTreeview
        self.series_tree = ttk.Treeview(series_list_frame, columns=("name", "trigger_count"), show="tree headings", height=15)
        self.series_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # シリーズTreeviewの設定
        self.series_tree.heading("#0", text="")
        self.series_tree.heading("name", text="シリーズ名")
        self.series_tree.heading("trigger_count", text="トリガー数")
        self.series_tree.column("#0", width=30)
        self.series_tree.column("name", width=200)
        self.series_tree.column("trigger_count", width=80)

        # スクロールバー
        series_scrollbar = ttk.Scrollbar(series_list_frame, orient=tk.VERTICAL, command=self.series_tree.yview)
        series_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.series_tree.configure(yscrollcommand=series_scrollbar.set)

        # シリーズ選択イベント
        self.series_tree.bind("<<TreeviewSelect>>", self.on_series_select)
        self.series_tree.bind("<Double-1>", self.on_series_double_click)

        # シリーズ管理ボタン
        series_buttons_frame = ttk.Frame(left_frame)
        series_buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(series_buttons_frame, text="シリーズ追加", command=self.add_series).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(series_buttons_frame, text="シリーズ編集", command=self.edit_series).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(series_buttons_frame, text="シリーズ削除", command=self.delete_series).pack(side=tk.LEFT, padx=(5, 0))

        # 右側：選択されたシリーズの詳細・トリガー一覧
        details_label = ttk.Label(right_frame, text="シリーズ詳細", font=("", 12, "bold"))
        details_label.pack(anchor=tk.W, pady=(0, 10))

        # シリーズ名表示
        self.series_name_var = tk.StringVar(value="シリーズを選択してください")
        ttk.Label(right_frame, textvariable=self.series_name_var, font=("", 11)).pack(anchor=tk.W, pady=(0, 10))

        # トリガー一覧
        triggers_label = ttk.Label(right_frame, text="含まれるトリガー", font=("", 10, "bold"))
        triggers_label.pack(anchor=tk.W, pady=(0, 5))

        # トリガーリストのフレーム
        triggers_list_frame = ttk.Frame(right_frame)
        triggers_list_frame.pack(fill=tk.BOTH, expand=True)

        # トリガーTreeview
        self.triggers_tree = ttk.Treeview(triggers_list_frame, columns=("name", "keywords", "response_type"), show="headings", height=20)
        self.triggers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # トリガーTreeviewの設定
        self.triggers_tree.heading("name", text="トリガー名")
        self.triggers_tree.heading("keywords", text="キーワード")
        self.triggers_tree.heading("response_type", text="応答タイプ")
        self.triggers_tree.column("name", width=150)
        self.triggers_tree.column("keywords", width=200)
        self.triggers_tree.column("response_type", width=100)

        # スクロールバー
        triggers_scrollbar = ttk.Scrollbar(triggers_list_frame, orient=tk.VERTICAL, command=self.triggers_tree.yview)
        triggers_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.triggers_tree.configure(yscrollcommand=triggers_scrollbar.set)

        # 閉じるボタン
        close_frame = ttk.Frame(self.dialog)
        close_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(close_frame, text="閉じる", command=self.close_dialog).pack(side=tk.RIGHT)

    def load_series_list(self):
        """シリーズ一覧を読み込み"""
        # 既存のアイテムを削除
        for item in self.series_tree.get_children():
            self.series_tree.delete(item)

        # シリーズデータを読み込み
        all_series = self.config_manager.get_all_trigger_series()

        for series_id, series_data in all_series.items():
            series_name = series_data.get("name", series_id)
            triggers = series_data.get("triggers", [])
            trigger_count = len(triggers)

            self.series_tree.insert("", tk.END, iid=series_id, values=(series_name, trigger_count))

    def on_series_select(self, event):
        """シリーズ選択時の処理"""
        selected = self.series_tree.selection()
        if not selected:
            self.series_name_var.set("シリーズを選択してください")
            self.clear_triggers_list()
            return

        series_id = selected[0]
        series_data = self.config_manager.get_trigger_series(series_id)

        series_name = series_data.get("name", series_id)
        self.series_name_var.set(f"シリーズ: {series_name}")

        self.load_triggers_list(series_data.get("triggers", []))

    def load_triggers_list(self, triggers):
        """トリガー一覧を読み込み"""
        # 既存のアイテムを削除
        for item in self.triggers_tree.get_children():
            self.triggers_tree.delete(item)

        for trigger in triggers:
            name = trigger.get("name", "無名トリガー")
            keywords = ", ".join(trigger.get("keywords", []))
            response_type = trigger.get("response_type", "predefined")

            self.triggers_tree.insert("", tk.END, values=(name, keywords, response_type))

    def clear_triggers_list(self):
        """トリガー一覧をクリア"""
        for item in self.triggers_tree.get_children():
            self.triggers_tree.delete(item)

    def on_series_double_click(self, event):
        """シリーズダブルクリック時の処理"""
        self.edit_series()

    def add_series(self):
        """シリーズ追加"""
        dialog = TriggerSeriesEditDialog(self.dialog, self.config_manager, None)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.load_series_list()

    def edit_series(self):
        """シリーズ編集"""
        selected = self.series_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "編集するシリーズを選択してください")
            return

        series_id = selected[0]
        dialog = TriggerSeriesEditDialog(self.dialog, self.config_manager, series_id)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.load_series_list()

    def delete_series(self):
        """シリーズ削除"""
        selected = self.series_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "削除するシリーズを選択してください")
            return

        series_id = selected[0]
        series_data = self.config_manager.get_trigger_series(series_id)
        series_name = series_data.get("name", series_id)

        if messagebox.askyesno("確認", f"シリーズ「{series_name}」を削除しますか？"):
            self.config_manager.delete_trigger_series(series_id)
            self.load_series_list()
            self.series_name_var.set("シリーズを選択してください")
            self.clear_triggers_list()

    def close_dialog(self):
        """ダイアログを閉じる"""
        self.dialog.destroy()


class TriggerSeriesEditDialog:
    def __init__(self, parent, config_manager, series_id=None):
        self.parent = parent
        self.config_manager = config_manager
        self.series_id = series_id
        self.result = None
        self.is_edit_mode = series_id is not None

        # 編集モードの場合、既存データを読み込み
        if self.is_edit_mode:
            self.series_data = self.config_manager.get_trigger_series(series_id).copy()
        else:
            self.series_data = {
                "name": "",
                "description": "",
                "triggers": []
            }

        # ダイアログ作成
        self.dialog = tk.Toplevel(parent)
        title = "シリーズ編集" if self.is_edit_mode else "シリーズ追加"
        self.dialog.title(title)
        self.dialog.geometry("800x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # ダイアログを中央に配置
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"800x500+{x}+{y}")

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """UI設定"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # シリーズ基本情報
        info_frame = ttk.LabelFrame(main_frame, text="シリーズ情報", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # シリーズ名
        ttk.Label(info_frame, text="シリーズ名:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.name_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 5))

        # 説明
        ttk.Label(info_frame, text="説明:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(5, 0))
        self.description_text = tk.Text(info_frame, height=3, width=50)
        self.description_text.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))

        info_frame.columnconfigure(1, weight=1)

        # トリガー一覧
        triggers_frame = ttk.LabelFrame(main_frame, text="含まれるトリガー", padding="10")
        triggers_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # トリガーTreeview
        self.triggers_tree = ttk.Treeview(triggers_frame, columns=("name", "keywords", "response_type"), show="headings", height=10)
        self.triggers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Treeviewの設定
        self.triggers_tree.heading("name", text="トリガー名")
        self.triggers_tree.heading("keywords", text="キーワード")
        self.triggers_tree.heading("response_type", text="応答タイプ")
        self.triggers_tree.column("name", width=150)
        self.triggers_tree.column("keywords", width=250)
        self.triggers_tree.column("response_type", width=100)

        # スクロールバー
        scrollbar = ttk.Scrollbar(triggers_frame, orient=tk.VERTICAL, command=self.triggers_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.triggers_tree.configure(yscrollcommand=scrollbar.set)

        # トリガー操作ボタン
        trigger_buttons_frame = ttk.Frame(main_frame)
        trigger_buttons_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(trigger_buttons_frame, text="トリガー追加", command=self.add_trigger).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(trigger_buttons_frame, text="トリガー編集", command=self.edit_trigger).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(trigger_buttons_frame, text="トリガー削除", command=self.delete_trigger).pack(side=tk.LEFT, padx=(5, 0))

        # 保存・キャンセルボタン
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(buttons_frame, text="キャンセル", command=self.cancel_dialog).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="保存", command=self.save_series).pack(side=tk.RIGHT)

    def load_data(self):
        """データを読み込み"""
        self.name_var.set(self.series_data.get("name", ""))
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(1.0, self.series_data.get("description", ""))

        self.load_triggers_list()

    def load_triggers_list(self):
        """トリガー一覧を読み込み"""
        # 既存のアイテムを削除
        for item in self.triggers_tree.get_children():
            self.triggers_tree.delete(item)

        for i, trigger in enumerate(self.series_data.get("triggers", [])):
            name = trigger.get("name", f"トリガー{i+1}")
            keywords = ", ".join(trigger.get("keywords", []))
            response_type = trigger.get("response_type", "predefined")

            self.triggers_tree.insert("", tk.END, iid=str(i), values=(name, keywords, response_type))

    def add_trigger(self):
        """トリガー追加"""
        dialog = TriggerEditDialog(self.dialog, None)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.series_data.setdefault("triggers", []).append(dialog.result)
            self.load_triggers_list()

    def edit_trigger(self):
        """トリガー編集"""
        selected = self.triggers_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "編集するトリガーを選択してください")
            return

        trigger_index = int(selected[0])
        trigger_data = self.series_data["triggers"][trigger_index]

        dialog = TriggerEditDialog(self.dialog, trigger_data)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.series_data["triggers"][trigger_index] = dialog.result
            self.load_triggers_list()

    def delete_trigger(self):
        """トリガー削除"""
        selected = self.triggers_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "削除するトリガーを選択してください")
            return

        trigger_index = int(selected[0])
        trigger_name = self.series_data["triggers"][trigger_index].get("name", f"トリガー{trigger_index+1}")

        if messagebox.askyesno("確認", f"トリガー「{trigger_name}」を削除しますか？"):
            del self.series_data["triggers"][trigger_index]
            self.load_triggers_list()

    def save_series(self):
        """シリーズを保存"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("エラー", "シリーズ名を入力してください")
            return

        description = self.description_text.get(1.0, tk.END).strip()

        # データを更新
        self.series_data["name"] = name
        self.series_data["description"] = description

        # 保存
        if not self.series_id:
            self.series_id = str(uuid.uuid4())

        self.config_manager.save_trigger_series_item(self.series_id, self.series_data)

        self.result = True
        self.dialog.destroy()

    def cancel_dialog(self):
        """キャンセル"""
        self.result = None
        self.dialog.destroy()


class TriggerEditDialog:
    def __init__(self, parent, trigger_data=None):
        self.parent = parent
        self.trigger_data = trigger_data.copy() if trigger_data else {}
        self.result = None

        # ダイアログ作成
        self.dialog = tk.Toplevel(parent)
        title = "トリガー編集" if trigger_data else "トリガー追加"
        self.dialog.title(title)
        self.dialog.geometry("600x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # ダイアログを中央に配置
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"600x400+{x}+{y}")

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """UI設定"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # トリガー名
        ttk.Label(main_frame, text="トリガー名:").grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 10))

        # キーワード
        ttk.Label(main_frame, text="キーワード:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(0, 10))
        self.keywords_text = tk.Text(main_frame, height=3, width=50)
        self.keywords_text.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 10))
        ttk.Label(main_frame, text="※1行1キーワード", font=("", 8)).grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 10))

        # キーワード条件
        ttk.Label(main_frame, text="キーワード条件:").grid(row=3, column=0, sticky=tk.W, pady=(0, 10))
        self.keyword_condition_var = tk.StringVar(value="OR")
        condition_frame = ttk.Frame(main_frame)
        condition_frame.grid(row=3, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 10))
        ttk.Radiobutton(condition_frame, text="OR (いずれかに一致)", variable=self.keyword_condition_var, value="OR").pack(anchor=tk.W)
        ttk.Radiobutton(condition_frame, text="AND (すべてに一致)", variable=self.keyword_condition_var, value="AND").pack(anchor=tk.W)

        # 応答タイプ
        ttk.Label(main_frame, text="応答タイプ:").grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
        self.response_type_var = tk.StringVar(value="predefined")
        response_frame = ttk.Frame(main_frame)
        response_frame.grid(row=4, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 10))
        ttk.Radiobutton(response_frame, text="定型メッセージ", variable=self.response_type_var, value="predefined").pack(anchor=tk.W)
        ttk.Radiobutton(response_frame, text="AI応答", variable=self.response_type_var, value="ai").pack(anchor=tk.W)

        # 定型メッセージ
        ttk.Label(main_frame, text="定型メッセージ:").grid(row=5, column=0, sticky=(tk.W, tk.N), pady=(0, 10))
        self.messages_text = tk.Text(main_frame, height=5, width=50)
        self.messages_text.grid(row=5, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 10))
        ttk.Label(main_frame, text="※1行1メッセージ", font=("", 8)).grid(row=6, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 10))

        main_frame.columnconfigure(1, weight=1)

        # 保存・キャンセルボタン
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(buttons_frame, text="キャンセル", command=self.cancel_dialog).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="保存", command=self.save_trigger).pack(side=tk.RIGHT)

    def load_data(self):
        """データを読み込み"""
        self.name_var.set(self.trigger_data.get("name", ""))

        # キーワード
        keywords = self.trigger_data.get("keywords", [])
        self.keywords_text.delete(1.0, tk.END)
        self.keywords_text.insert(1.0, "\n".join(keywords))

        # キーワード条件
        self.keyword_condition_var.set(self.trigger_data.get("keyword_condition", "OR"))

        # 応答タイプ
        self.response_type_var.set(self.trigger_data.get("response_type", "predefined"))

        # 定型メッセージ
        messages = self.trigger_data.get("messages", [])
        self.messages_text.delete(1.0, tk.END)
        self.messages_text.insert(1.0, "\n".join(messages))

    def save_trigger(self):
        """トリガーを保存"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("エラー", "トリガー名を入力してください")
            return

        # キーワード
        keywords_text = self.keywords_text.get(1.0, tk.END).strip()
        keywords = [k.strip() for k in keywords_text.split("\n") if k.strip()]
        if not keywords:
            messagebox.showerror("エラー", "キーワードを入力してください")
            return

        # 定型メッセージ
        messages_text = self.messages_text.get(1.0, tk.END).strip()
        messages = [m.strip() for m in messages_text.split("\n") if m.strip()]

        # データを構築
        self.result = {
            "id": self.trigger_data.get("id", str(uuid.uuid4())),
            "name": name,
            "enabled": self.trigger_data.get("enabled", True),
            "keywords": keywords,
            "keyword_condition": self.keyword_condition_var.get(),
            "response_type": self.response_type_var.get(),
            "messages": messages,
            "ai_response_prompt": self.trigger_data.get("ai_response_prompt", ""),
            "max_reactions_per_stream": self.trigger_data.get("max_reactions_per_stream", 1),
            "response_delay_seconds": self.trigger_data.get("response_delay_seconds", 0),
            "firing_probability": self.trigger_data.get("firing_probability", 100)
        }

        self.dialog.destroy()

    def cancel_dialog(self):
        """キャンセル"""
        self.result = None
        self.dialog.destroy()