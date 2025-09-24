"""
トリガーシリーズ選択ダイアログ
"""
import tkinter as tk
from tkinter import ttk, messagebox


class TriggerSeriesSelectionDialog:
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None

        # ダイアログ作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("トリガーシリーズ選択")
        self.dialog.geometry("600x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # ダイアログを中央に配置
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"600x400+{x}+{y}")

        self.setup_ui()
        self.load_series_list()

    def setup_ui(self):
        """UI設定"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 説明ラベル
        ttk.Label(main_frame, text="追加するトリガーシリーズを選択してください", font=("", 11)).pack(anchor=tk.W, pady=(0, 10))

        # シリーズ一覧
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview
        self.series_tree = ttk.Treeview(list_frame, columns=("name", "trigger_count", "description"), show="headings", height=15)
        self.series_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Treeview設定
        self.series_tree.heading("name", text="シリーズ名")
        self.series_tree.heading("trigger_count", text="トリガー数")
        self.series_tree.heading("description", text="説明")
        self.series_tree.column("name", width=150)
        self.series_tree.column("trigger_count", width=80)
        self.series_tree.column("description", width=250)

        # スクロールバー
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.series_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.series_tree.configure(yscrollcommand=scrollbar.set)

        # ダブルクリックで選択
        self.series_tree.bind("<Double-1>", self.on_series_double_click)

        # プレビューエリア
        preview_frame = ttk.LabelFrame(main_frame, text="含まれるトリガー", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # トリガー一覧
        preview_list_frame = ttk.Frame(preview_frame)
        preview_list_frame.pack(fill=tk.BOTH, expand=True)

        self.triggers_tree = ttk.Treeview(preview_list_frame, columns=("name", "keywords"), show="headings", height=6)
        self.triggers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.triggers_tree.heading("name", text="トリガー名")
        self.triggers_tree.heading("keywords", text="キーワード")
        self.triggers_tree.column("name", width=150)
        self.triggers_tree.column("keywords", width=300)

        preview_scrollbar = ttk.Scrollbar(preview_list_frame, orient=tk.VERTICAL, command=self.triggers_tree.yview)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.triggers_tree.configure(yscrollcommand=preview_scrollbar.set)

        # シリーズ選択イベント
        self.series_tree.bind("<<TreeviewSelect>>", self.on_series_select)

        # ボタン
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(buttons_frame, text="キャンセル", command=self.cancel_selection).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="選択", command=self.confirm_selection).pack(side=tk.RIGHT)

    def load_series_list(self):
        """シリーズ一覧を読み込み"""
        # 既存のアイテムを削除
        for item in self.series_tree.get_children():
            self.series_tree.delete(item)

        # シリーズデータを読み込み
        all_series = self.config_manager.get_all_trigger_series()

        if not all_series:
            # シリーズが存在しない場合のメッセージ
            self.series_tree.insert("", tk.END, values=("シリーズが登録されていません", "", "メイン画面の「シリーズ管理」からシリーズを作成してください"))
            return

        for series_id, series_data in all_series.items():
            series_name = series_data.get("name", series_id)
            triggers = series_data.get("triggers", [])
            trigger_count = len(triggers)
            description = series_data.get("description", "")[:50]  # 説明は50文字まで

            self.series_tree.insert("", tk.END, iid=series_id, values=(series_name, trigger_count, description))

    def on_series_select(self, event):
        """シリーズ選択時の処理"""
        selected = self.series_tree.selection()
        if not selected:
            self.clear_triggers_preview()
            return

        series_id = selected[0]

        # シリーズが存在しない場合（"シリーズが登録されていません"の行）
        all_series = self.config_manager.get_all_trigger_series()
        if series_id not in all_series:
            self.clear_triggers_preview()
            return

        series_data = self.config_manager.get_trigger_series(series_id)
        triggers = series_data.get("triggers", [])

        self.load_triggers_preview(triggers)

    def load_triggers_preview(self, triggers):
        """トリガープレビューを読み込み"""
        # 既存のアイテムを削除
        for item in self.triggers_tree.get_children():
            self.triggers_tree.delete(item)

        for trigger in triggers:
            name = trigger.get("name", "無名トリガー")
            keywords = ", ".join(trigger.get("keywords", []))

            self.triggers_tree.insert("", tk.END, values=(name, keywords))

    def clear_triggers_preview(self):
        """トリガープレビューをクリア"""
        for item in self.triggers_tree.get_children():
            self.triggers_tree.delete(item)

    def on_series_double_click(self, event):
        """シリーズダブルクリック時の処理"""
        self.confirm_selection()

    def confirm_selection(self):
        """選択を確定"""
        selected = self.series_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "シリーズを選択してください")
            return

        series_id = selected[0]

        # シリーズが存在するかチェック
        all_series = self.config_manager.get_all_trigger_series()
        if series_id not in all_series:
            messagebox.showwarning("警告", "有効なシリーズを選択してください")
            return

        self.result = series_id
        self.dialog.destroy()

    def cancel_selection(self):
        """選択をキャンセル"""
        self.result = None
        self.dialog.destroy()