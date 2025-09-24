"""
トリガー管理ダイアログ
"""
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox

from .utils import log_to_gui
from .trigger_edit_dialog import TriggerEditDialog


class TriggerManagementDialog:
    def __init__(self, parent, config_manager, user_id, broadcaster_id, broadcaster_name):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.broadcaster_id = broadcaster_id
        self.broadcaster_name = broadcaster_name

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"トリガー管理 - {broadcaster_name}")
        self.dialog.geometry("800x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()
        self.refresh_triggers_list()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # トリガー一覧
        list_frame = ttk.LabelFrame(main_frame, text="トリガー一覧", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.triggers_tree = ttk.Treeview(
            list_frame,
            columns=("name", "enabled", "keywords", "condition", "response_type"),
            show="tree headings",
            height=10
        )
        self.triggers_tree.heading("#0", text="有効")
        self.triggers_tree.heading("name", text="名前")
        self.triggers_tree.heading("enabled", text="状態")
        self.triggers_tree.heading("keywords", text="キーワード")
        self.triggers_tree.heading("condition", text="条件")
        self.triggers_tree.heading("response_type", text="応答タイプ")

        self.triggers_tree.column("#0", width=60)
        self.triggers_tree.column("name", width=150)
        self.triggers_tree.column("enabled", width=60)
        self.triggers_tree.column("keywords", width=200)
        self.triggers_tree.column("condition", width=60)
        self.triggers_tree.column("response_type", width=100)

        # チェックボックスクリックイベント
        self.triggers_tree.bind("<Button-1>", self.on_trigger_click)

        self.triggers_tree.pack(fill=tk.BOTH, expand=True)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="トリガー追加", command=self.add_trigger).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="一括有効", command=self.enable_all_triggers).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="一括無効", command=self.disable_all_triggers).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="トリガー編集", command=self.edit_trigger).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="トリガー削除", command=self.delete_trigger).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="閉じる", command=self.close_dialog).pack(side=tk.RIGHT)

    def refresh_triggers_list(self):
        """トリガー一覧を更新"""
        for item in self.triggers_tree.get_children():
            self.triggers_tree.delete(item)

        triggers = self.config_manager.get_broadcaster_triggers(self.user_id, self.broadcaster_id)
        for trigger in triggers:
            name = trigger.get("name", "無名トリガー")
            enabled = trigger.get("enabled", True)
            keywords = ", ".join(trigger.get("keywords", []))
            condition = trigger.get("keyword_condition", "OR")
            response_type = "定型" if trigger.get("response_type", "predefined") == "predefined" else "AI"

            # チェックボックス表示
            checkbox = "☑" if enabled else "☐"
            status = "有効" if enabled else "無効"

            self.triggers_tree.insert(
                "",
                tk.END,
                text=checkbox,
                values=(name, status, keywords, condition, response_type)
            )

    def on_trigger_click(self, event):
        """トリガーのチェックボックスクリック処理"""
        item = self.triggers_tree.identify('item', event.x, event.y)
        column = self.triggers_tree.identify('column', event.x, event.y)

        # チェックボックス列（#0）がクリックされた場合
        if item and column == "#0":
            # 選択されたトリガーのインデックスを取得
            selected_index = self.triggers_tree.index(item)
            triggers = self.config_manager.get_broadcaster_triggers(self.user_id, self.broadcaster_id)

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
                    self.update_trigger_enabled_status(trigger_id, new_enabled)

    def update_trigger_enabled_status(self, trigger_id: str, enabled: bool):
        """トリガーの有効/無効状態を更新"""
        try:
            triggers = self.config_manager.get_broadcaster_triggers(self.user_id, self.broadcaster_id)
            for trigger in triggers:
                if trigger.get("id") == trigger_id:
                    trigger["enabled"] = enabled
                    self.config_manager.save_trigger_config(self.user_id, self.broadcaster_id, trigger)

                    status_text = "有効" if enabled else "無効"
                    log_to_gui(f"トリガー {trigger.get('name', '')} を{status_text}に変更しました")
                    break
        except Exception as e:
            messagebox.showerror("エラー", f"設定更新エラー: {str(e)}")

    def enable_all_triggers(self):
        """全トリガーを一括有効化"""
        try:
            triggers = self.config_manager.get_broadcaster_triggers(self.user_id, self.broadcaster_id)
            updated_count = 0

            for trigger in triggers:
                if not trigger.get("enabled", True):
                    trigger["enabled"] = True
                    self.config_manager.save_trigger_config(self.user_id, self.broadcaster_id, trigger)
                    updated_count += 1

            self.refresh_triggers_list()
            log_to_gui(f"{updated_count}個のトリガーを有効化しました")
        except Exception as e:
            log_to_gui(f"一括有効化エラー: {str(e)}")

    def disable_all_triggers(self):
        """全トリガーを一括無効化"""
        triggers = self.config_manager.get_broadcaster_triggers(self.user_id, self.broadcaster_id)
        if not triggers:
            log_to_gui("トリガーが登録されていません")
            return

        # 確認なしで一括無効化
        try:
            updated_count = 0
            for trigger in triggers:
                if trigger.get("enabled", True):
                    trigger["enabled"] = False
                    self.config_manager.save_trigger_config(self.user_id, self.broadcaster_id, trigger)
                    updated_count += 1

            self.refresh_triggers_list()
            log_to_gui(f"{updated_count}個のトリガーを無効化しました")
        except Exception as e:
            log_to_gui(f"一括無効化エラー: {str(e)}")

    def add_trigger(self):
        """トリガー追加"""
        dialog = TriggerEditDialog(self.dialog, self.config_manager, self.user_id, self.broadcaster_id)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_triggers_list()

    def edit_trigger(self):
        """トリガー編集"""
        selected = self.triggers_tree.selection()
        if not selected:
            log_to_gui("編集するトリガーを選択してください")
            return

        # 選択されたトリガーのインデックスを取得
        selected_index = self.triggers_tree.index(selected[0])
        triggers = self.config_manager.get_broadcaster_triggers(self.user_id, self.broadcaster_id)

        if selected_index < len(triggers):
            trigger = triggers[selected_index]
            trigger_id = trigger.get("id")

            dialog = TriggerEditDialog(self.dialog, self.config_manager, self.user_id, self.broadcaster_id, trigger_id)
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
        triggers = self.config_manager.get_broadcaster_triggers(self.user_id, self.broadcaster_id)

        if selected_index < len(triggers):
            trigger = triggers[selected_index]
            trigger_name = trigger.get("name", "無名トリガー")
            trigger_id = trigger.get("id")

            # 確認なしで削除
            if trigger_id:
                self.config_manager.delete_trigger_config(self.user_id, self.broadcaster_id, trigger_id)
                self.refresh_triggers_list()

    def close_dialog(self):
        self.result = True
        self.dialog.destroy()