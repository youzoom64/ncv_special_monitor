"""
配信者管理ダイアログ
"""
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox

from .utils import log_to_gui
from .trigger_dialog import TriggerManagementDialog
from .simple_dialogs import SimpleBroadcasterEditDialog
from bulk_broadcaster_registration import show_bulk_registration_dialog


class BroadcasterManagementDialog:
    def __init__(self, parent, config_manager, user_id, user_display_name):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.user_display_name = user_display_name

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"配信者管理 - {user_display_name}")
        self.dialog.geometry("1000x500")  # 幅を広げる
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()
        self.refresh_broadcasters_list()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左右分割
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # === 左側：配信者一覧 ===
        list_frame = ttk.LabelFrame(left_frame, text="配信者一覧", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.broadcasters_tree = ttk.Treeview(
            list_frame,
            columns=("broadcaster_id", "broadcaster_name", "enabled", "triggers"),
            show="tree headings",
            height=10
        )
        self.broadcasters_tree.heading("#0", text="有効")
        self.broadcasters_tree.heading("broadcaster_id", text="配信者ID")
        self.broadcasters_tree.heading("broadcaster_name", text="配信者名")
        self.broadcasters_tree.heading("enabled", text="状態")
        self.broadcasters_tree.heading("triggers", text="トリガー数")

        self.broadcasters_tree.column("#0", width=60)
        self.broadcasters_tree.column("broadcaster_id", width=100)
        self.broadcasters_tree.column("broadcaster_name", width=200)
        self.broadcasters_tree.column("enabled", width=60)
        self.broadcasters_tree.column("triggers", width=80)

        # チェックボックスクリックイベント
        self.broadcasters_tree.bind("<Button-1>", self.on_broadcaster_click)

        self.broadcasters_tree.pack(fill=tk.BOTH, expand=True)

        # ボタン
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="配信者追加", command=self.add_broadcaster).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="一括登録", command=self.bulk_register_broadcasters).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="一括有効", command=self.enable_all_broadcasters).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="一括無効", command=self.disable_all_broadcasters).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="配信者編集", command=self.edit_broadcaster).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="配信者削除", command=self.delete_broadcaster).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="トリガー管理", command=self.manage_triggers).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="閉じる", command=self.close_dialog).pack(side=tk.RIGHT)

        # === 右側：トリガー一覧 ===
        triggers_frame = ttk.LabelFrame(right_frame, text="選択された配信者のトリガー一覧", padding="5")
        triggers_frame.pack(fill=tk.BOTH, expand=True)

        # トリガー一覧Treeview
        self.triggers_tree = ttk.Treeview(
            triggers_frame,
            columns=("trigger_name", "enabled", "keywords", "response_type"),
            show="headings",
            height=15
        )
        self.triggers_tree.heading("trigger_name", text="トリガー名")
        self.triggers_tree.heading("enabled", text="有効")
        self.triggers_tree.heading("keywords", text="キーワード")
        self.triggers_tree.heading("response_type", text="応答タイプ")

        self.triggers_tree.column("trigger_name", width=120)
        self.triggers_tree.column("enabled", width=50)
        self.triggers_tree.column("keywords", width=150)
        self.triggers_tree.column("response_type", width=80)

        self.triggers_tree.pack(fill=tk.BOTH, expand=True)

        # ダブルクリックでトリガー管理画面へ
        self.triggers_tree.bind("<Double-1>", self.on_trigger_double_click)

        # 配信者選択でトリガー一覧更新
        self.broadcasters_tree.bind("<<TreeviewSelect>>", self.on_broadcaster_select)

        # トリガー一覧を初期表示（選択されていない状態）
        self.refresh_triggers_for_selected_broadcaster()

    def on_broadcaster_select(self, event):
        """配信者選択時の処理"""
        self.refresh_triggers_for_selected_broadcaster()

    def refresh_triggers_for_selected_broadcaster(self):
        """選択された配信者のトリガー一覧を更新"""
        # 既存の項目をクリア
        for item in self.triggers_tree.get_children():
            self.triggers_tree.delete(item)

        # 選択された配信者を取得
        selection = self.broadcasters_tree.selection()
        if not selection:
            return

        # 選択された配信者の情報を取得
        selected_item = self.broadcasters_tree.item(selection[0])
        broadcaster_id = selected_item["values"][0] if selected_item["values"] else None

        if not broadcaster_id:
            return

        # ユーザー設定から配信者のトリガーを取得
        user_config = self.config_manager.get_user_config(self.user_id)
        broadcasters = user_config.get("broadcasters", {})
        broadcaster_info = broadcasters.get(broadcaster_id, {})
        triggers = broadcaster_info.get("triggers", [])

        # トリガー一覧を表示
        for trigger in triggers:
            trigger_name = trigger.get("name", "無名トリガー")
            enabled = "有効" if trigger.get("enabled", True) else "無効"
            keywords = ", ".join(trigger.get("keywords", [])[:3])  # 最初の3つのキーワードを表示
            if len(trigger.get("keywords", [])) > 3:
                keywords += "..."
            response_type = trigger.get("response_type", "定型")

            self.triggers_tree.insert(
                "",
                tk.END,
                values=(trigger_name, enabled, keywords, response_type)
            )

    def on_trigger_double_click(self, event):
        """トリガーダブルクリック処理"""
        selection = self.triggers_tree.selection()
        if not selection:
            return

        # 選択された配信者を取得
        broadcaster_selection = self.broadcasters_tree.selection()
        if not broadcaster_selection:
            log_to_gui("配信者が選択されていません")
            return

        # 選択された配信者の情報を取得
        broadcaster_item = self.broadcasters_tree.item(broadcaster_selection[0])
        broadcaster_id = broadcaster_item["values"][0] if broadcaster_item["values"] else None
        broadcaster_name = broadcaster_item["values"][1] if len(broadcaster_item["values"]) > 1 else f"配信者{broadcaster_id}"

        if not broadcaster_id:
            log_to_gui("配信者IDが取得できません")
            return

        # トリガー管理ダイアログを開く
        dialog = TriggerManagementDialog(self.dialog, self.config_manager, self.user_id, broadcaster_id, broadcaster_name)
        self.dialog.wait_window(dialog.dialog)

        # ダイアログが閉じられた後、トリガー一覧を更新
        self.refresh_triggers_for_selected_broadcaster()

    def refresh_broadcasters_list(self):
        """配信者一覧を更新"""
        for item in self.broadcasters_tree.get_children():
            self.broadcasters_tree.delete(item)

        broadcasters = self.config_manager.get_user_broadcasters(self.user_id)
        for broadcaster_id, broadcaster_config in broadcasters.items():
            name = broadcaster_config.get("broadcaster_name", f"配信者{broadcaster_id}")
            enabled = broadcaster_config.get("enabled", True)
            triggers_count = len(broadcaster_config.get("triggers", []))

            # チェックボックス表示
            checkbox = "☑" if enabled else "☐"
            status = "有効" if enabled else "無効"

            self.broadcasters_tree.insert(
                "",
                tk.END,
                text=checkbox,
                values=(broadcaster_id, name, status, f"{triggers_count}個")
            )

    def on_broadcaster_click(self, event):
        """配信者のチェックボックスクリック処理"""
        item = self.broadcasters_tree.identify('item', event.x, event.y)
        column = self.broadcasters_tree.identify('column', event.x, event.y)

        # チェックボックス列（#0）がクリックされた場合
        if item and column == "#0":
            values = self.broadcasters_tree.item(item, "values")
            if len(values) >= 2:
                broadcaster_id = values[0]
                broadcaster_name = values[1]

                # 現在の状態を取得
                current_text = self.broadcasters_tree.item(item, "text")
                current_enabled = current_text == "☑"

                # 状態を切り替え
                new_enabled = not current_enabled
                new_checkbox = "☑" if new_enabled else "☐"
                new_status = "有効" if new_enabled else "無効"

                # 表示を更新
                self.broadcasters_tree.item(item, text=new_checkbox)
                self.broadcasters_tree.item(item, values=(
                    broadcaster_id, broadcaster_name, new_status, values[3]
                ))

                # 設定を保存
                self.update_broadcaster_enabled_status(broadcaster_id, new_enabled)

    def update_broadcaster_enabled_status(self, broadcaster_id: str, enabled: bool):
        """配信者の有効/無効状態を更新"""
        try:
            # 現在の配信者設定を取得
            broadcasters = self.config_manager.get_user_broadcasters(self.user_id)
            if broadcaster_id in broadcasters:
                broadcaster_config = broadcasters[broadcaster_id]
                broadcaster_config["enabled"] = enabled

                # 設定を保存
                self.config_manager.save_broadcaster_config(self.user_id, broadcaster_id, broadcaster_config)

                status_text = "有効" if enabled else "無効"
                log_to_gui(f"配信者 {broadcaster_id} を{status_text}に変更しました")
        except Exception as e:
            messagebox.showerror("エラー", f"設定更新エラー: {str(e)}")

    def enable_all_broadcasters(self):
        """全配信者を一括有効化"""
        try:
            broadcasters = self.config_manager.get_user_broadcasters(self.user_id)
            updated_count = 0

            for broadcaster_id, broadcaster_config in broadcasters.items():
                if not broadcaster_config.get("enabled", True):
                    broadcaster_config["enabled"] = True
                    self.config_manager.save_broadcaster_config(self.user_id, broadcaster_id, broadcaster_config)
                    updated_count += 1

            self.refresh_broadcasters_list()
            log_to_gui(f"{updated_count}人の配信者を有効化しました")
        except Exception as e:
            log_to_gui(f"一括有効化エラー: {str(e)}")

    def disable_all_broadcasters(self):
        """全配信者を一括無効化"""
        broadcasters = self.config_manager.get_user_broadcasters(self.user_id)
        if not broadcasters:
            log_to_gui("配信者が登録されていません")
            return

        # 確認なしで一括無効化
        try:
            updated_count = 0
            for broadcaster_id, broadcaster_config in broadcasters.items():
                if broadcaster_config.get("enabled", True):
                    broadcaster_config["enabled"] = False
                    self.config_manager.save_broadcaster_config(self.user_id, broadcaster_id, broadcaster_config)
                    updated_count += 1

            self.refresh_broadcasters_list()
            log_to_gui(f"{updated_count}人の配信者を無効化しました")
        except Exception as e:
            log_to_gui(f"一括無効化エラー: {str(e)}")

    def add_broadcaster(self):
        """配信者追加"""
        from .broadcaster_edit_dialog import BroadcasterEditDialog
        
        dialog = BroadcasterEditDialog(self.dialog, self.config_manager, self.user_id)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_broadcasters_list()

    def edit_broadcaster(self):
        """配信者編集"""
        from .broadcaster_edit_dialog import BroadcasterEditDialog
        
        selected = self.broadcasters_tree.selection()
        if not selected:
            log_to_gui("編集する配信者を選択してください")
            return

        values = self.broadcasters_tree.item(selected[0], "values")
        broadcaster_id = values[0]

        dialog = BroadcasterEditDialog(self.dialog, self.config_manager, self.user_id, broadcaster_id)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_broadcasters_list()

    def delete_broadcaster(self):
        """配信者削除"""
        selected = self.broadcasters_tree.selection()
        if not selected:
            log_to_gui("削除する配信者を選択してください")
            return

        values = self.broadcasters_tree.item(selected[0], "values")
        broadcaster_id = values[0]
        broadcaster_name = values[1]

        # 確認なしで削除
        self.config_manager.delete_broadcaster_config(self.user_id, broadcaster_id)
        self.refresh_broadcasters_list()

    def manage_triggers(self):
        """トリガー管理"""
        selected = self.broadcasters_tree.selection()
        if not selected:
            log_to_gui("トリガー管理する配信者を選択してください")
            return

        values = self.broadcasters_tree.item(selected[0], "values")
        broadcaster_id = values[0]
        broadcaster_name = values[1]

        dialog = TriggerManagementDialog(self.dialog, self.config_manager, self.user_id, broadcaster_id, broadcaster_name)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_broadcasters_list()

    def bulk_register_broadcasters(self):
        """一括配信者登録"""
        result = show_bulk_registration_dialog(
            self.dialog, self.config_manager, self.user_id, self.user_display_name
        )
        if result:
            self.refresh_broadcasters_list()

    def close_dialog(self):
        self.result = True
        self.dialog.destroy()