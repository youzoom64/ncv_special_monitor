"""
配信者編集ダイアログ
"""
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as msgbox
import requests
from bs4 import BeautifulSoup

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
        self.dialog.geometry("1000x700")
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
        broadcaster_id_frame = ttk.Frame(basic_frame)
        broadcaster_id_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        self.broadcaster_id_entry = ttk.Entry(broadcaster_id_frame, textvariable=self.broadcaster_id_var)
        self.broadcaster_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(broadcaster_id_frame, text="名前取得", command=self.fetch_broadcaster_name).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(basic_frame, text="配信者名:").grid(row=1, column=0, sticky=tk.W)
        self.broadcaster_name_var = tk.StringVar(value=self.broadcaster_config.get("broadcaster_name", ""))
        ttk.Entry(basic_frame, textvariable=self.broadcaster_name_var).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        self.enabled_var = tk.BooleanVar(value=self.broadcaster_config.get("enabled", True))
        ttk.Checkbutton(basic_frame, text="有効", variable=self.enabled_var).grid(row=2, column=1, sticky=tk.W, padx=(5, 0))

        basic_frame.columnconfigure(1, weight=1)

        # デフォルト応答設定（配信者用）
        response_frame = ttk.LabelFrame(left_frame, text="この配信者でのデフォルト応答設定", padding="5")
        response_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # AI分析カスタムプロンプト
        self.ai_analysis_enabled_var = tk.BooleanVar(value=self.broadcaster_config.get("default_response", {}).get("ai_analysis_enabled", False))
        ttk.Checkbutton(response_frame, text="AI分析カスタムプロンプトを使用", variable=self.ai_analysis_enabled_var).pack(anchor=tk.W, pady=(0, 2))

        ttk.Label(response_frame, text="AI分析カスタムプロンプト:").pack(anchor=tk.W)
        self.ai_analysis_prompt_text = tk.Text(response_frame, height=8, wrap=tk.WORD)
        self.ai_analysis_prompt_text.pack(fill=tk.X, pady=(2, 2))
        ai_analysis_prompt = self.broadcaster_config.get("default_response", {}).get("ai_analysis_prompt", "")
        self.ai_analysis_prompt_text.insert("1.0", ai_analysis_prompt)

        # AI分析プロンプトの説明
        analysis_help_text = "この配信者に対するAI分析時の指示。配信の特徴や話題を指定することで精度が向上します。"
        analysis_help_label = ttk.Label(response_frame, text=analysis_help_text, font=("", 8), foreground="gray")
        analysis_help_label.pack(anchor=tk.W, pady=(0, 10))

        # 定型メッセージ応答有効/無効チェックボックス
        self.default_response_enabled_var = tk.BooleanVar(value=self.broadcaster_config.get("default_response", {}).get("enabled", False))
        ttk.Checkbutton(response_frame, text="定型メッセージを有効にする", variable=self.default_response_enabled_var).pack(anchor=tk.W, pady=(0, 5))

        # 応答タイプ
        type_frame = ttk.Frame(response_frame)
        type_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(type_frame, text="応答タイプ:").pack(side=tk.LEFT)
        self.response_type_var = tk.StringVar(value=self.broadcaster_config.get("default_response", {}).get("response_type", "predefined"))
        ttk.Radiobutton(type_frame, text="定型メッセージ", variable=self.response_type_var, value="predefined").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(type_frame, text="AI生成", variable=self.response_type_var, value="ai").pack(side=tk.LEFT)

        # メッセージ設定
        ttk.Label(response_frame, text="定型メッセージ (1行1メッセージ):").pack(anchor=tk.W)
        self.messages_text = tk.Text(response_frame, height=2)
        self.messages_text.pack(fill=tk.X, pady=(0, 5))
        messages = self.broadcaster_config.get("default_response", {}).get("messages", [])
        self.messages_text.insert("1.0", "\n".join(messages))

        ttk.Label(response_frame, text="AI応答プロンプト:").pack(anchor=tk.W)
        self.ai_prompt_text = tk.Text(response_frame, height=3, wrap=tk.WORD)
        self.ai_prompt_text.pack(fill=tk.X, pady=2)
        ai_prompt = self.broadcaster_config.get("default_response", {}).get("ai_response_prompt", "")
        self.ai_prompt_text.insert("1.0", ai_prompt)

        # AIプロンプト変数説明
        prompt_help_text = "使用可能な変数: {no}, {user_name}, {user_id}, {comment_content}, {time}, {date}, {datetime}, {broadcaster_name}"
        help_label = ttk.Label(response_frame, text=prompt_help_text, font=("", 8), foreground="gray")
        help_label.pack(anchor=tk.W, pady=(2, 5))

        # 反応設定
        reaction_frame = ttk.Frame(response_frame)
        reaction_frame.pack(fill=tk.X)

        ttk.Label(reaction_frame, text="最大反応回数:").grid(row=0, column=0, sticky=tk.W)
        self.max_reactions_var = tk.StringVar(value=str(self.broadcaster_config.get("default_response", {}).get("max_reactions_per_stream", 1)))
        ttk.Entry(reaction_frame, textvariable=self.max_reactions_var, width=10).grid(row=0, column=1, padx=(5, 10))

        ttk.Label(reaction_frame, text="応答遅延(秒):").grid(row=0, column=2, sticky=tk.W)
        self.delay_var = tk.StringVar(value=str(self.broadcaster_config.get("default_response", {}).get("response_delay_seconds", 0)))
        ttk.Entry(reaction_frame, textvariable=self.delay_var, width=10).grid(row=0, column=3, padx=(5, 0))

        ttk.Label(reaction_frame, text="分割送信間隔(秒):").grid(row=0, column=4, sticky=tk.W)
        self.split_delay_var = tk.StringVar(
            value=str(self.broadcaster_config.get("default_response", {}).get("response_split_delay_seconds", 1))
        )
        ttk.Entry(reaction_frame, textvariable=self.split_delay_var, width=10).grid(row=0, column=5, padx=(5, 0))

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
        ttk.Button(trigger_button_frame, text="シリーズ追加", command=self.add_trigger_series).pack(side=tk.LEFT, padx=(2, 2))
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

        # AI分析プロンプトを取得
        ai_analysis_prompt = self.ai_analysis_prompt_text.get("1.0", tk.END).strip()

        # AI応答プロンプトを取得
        ai_response_prompt = self.ai_prompt_text.get("1.0", tk.END).strip()

        # 最新のトリガー情報を取得
        current_triggers = self.config_manager.get_broadcaster_triggers(self.user_id, broadcaster_id)
        print(f"[GUI DEBUG] Current triggers count: {len(current_triggers)}")

        # 設定を作成
        broadcaster_config = {
            "broadcaster_id": broadcaster_id,
            "broadcaster_name": broadcaster_name,
            "enabled": self.enabled_var.get(),
            "default_response": {
                "enabled": self.default_response_enabled_var.get(),
                "response_type": self.response_type_var.get(),
                "messages": messages,
                "ai_response_prompt": ai_response_prompt,
                "ai_analysis_enabled": self.ai_analysis_enabled_var.get(),
                "ai_analysis_prompt": ai_analysis_prompt,
                "max_reactions_per_stream": int(self.max_reactions_var.get() or 1),
                "response_delay_seconds": int(self.delay_var.get() or 0),
                "response_split_delay_seconds": int(self.split_delay_var.get() or 1)
            },
            "triggers": current_triggers  # 最新のトリガー情報を使用
        }
        print(f"[GUI DEBUG] Saving broadcaster config with {len(current_triggers)} triggers")

        self.config_manager.save_broadcaster_config(self.user_id, broadcaster_id, broadcaster_config)
        self.result = True
        self.dialog.destroy()

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
        """トリガーダブルクリック処理 - 直接トリガー編集画面に遷移"""
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

        # 選択されたトリガーの情報を取得
        item_values = self.triggers_tree.item(selection[0], "values")
        trigger_name = item_values[0]

        # トリガーのインデックスを特定
        user_config = self.config_manager.get_user_config(self.user_id)
        broadcasters = user_config.get("broadcasters", {})
        broadcaster_info = broadcasters.get(broadcaster_id, {})
        triggers = broadcaster_info.get("triggers", [])

        trigger_index = None
        for i, trigger in enumerate(triggers):
            if trigger.get("name", "") == trigger_name:
                trigger_index = i
                break

        if trigger_index is None:
            log_to_gui("トリガーが見つかりません")
            return

        # トリガー編集ダイアログを直接開く
        dialog = SimpleTriggerEditDialog(self.dialog, self.config_manager, self.user_id, broadcaster_id, broadcaster_name, trigger_index)
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

    def add_trigger_series(self):
        """トリガーシリーズ追加"""
        from tkinter import messagebox
        from .trigger_series_selection_dialog import TriggerSeriesSelectionDialog

        broadcaster_id = self.broadcaster_id or self.broadcaster_id_var.get().strip()
        if not broadcaster_id:
            log_to_gui("配信者IDが設定されていません")
            return

        # シリーズ選択ダイアログ
        dialog = TriggerSeriesSelectionDialog(self.dialog, self.config_manager)
        self.dialog.wait_window(dialog.dialog)

        if dialog.result:
            series_id = dialog.result
            series_data = self.config_manager.get_trigger_series(series_id)
            series_name = series_data.get("name", series_id)
            triggers = series_data.get("triggers", [])

            if not triggers:
                messagebox.showwarning("警告", f"シリーズ「{series_name}」にはトリガーが含まれていません")
                return

            # 現在の配信者の設定を取得
            user_config = self.config_manager.get_user_config(self.user_id)
            broadcasters = user_config.get("broadcasters", {})
            broadcaster_config = broadcasters.get(broadcaster_id, {})
            existing_triggers = broadcaster_config.get("triggers", [])

            # シリーズのトリガーを追加
            added_count = 0
            for trigger in triggers:
                # 同じ名前のトリガーがすでに存在するかチェック
                trigger_name = trigger.get("name", "")
                name_exists = any(t.get("name") == trigger_name for t in existing_triggers)

                if not name_exists:
                    # 新しいトリガーとして追加
                    new_trigger = trigger.copy()
                    existing_triggers.append(new_trigger)
                    added_count += 1

            if added_count > 0:
                # 設定を保存
                broadcaster_config["triggers"] = existing_triggers
                broadcasters[broadcaster_id] = broadcaster_config
                user_config["broadcasters"] = broadcasters
                self.config_manager.save_user_config_to_directory(self.user_id, user_config)

                log_to_gui(f"シリーズ「{series_name}」から {added_count} 個のトリガーを追加しました")
                self.refresh_triggers_list()
            else:
                messagebox.showinfo("情報", f"シリーズ「{series_name}」のトリガーはすでにすべて追加済みです")

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

        # トリガーIDを取得（TreeViewのitemからIDを取得）
        trigger_id = None
        triggers = self.config_manager.get_broadcaster_triggers(self.user_id, broadcaster_id)
        for trigger in triggers:
            if trigger.get("name", "") == trigger_name:
                trigger_id = trigger.get("id")
                break

        if not trigger_id:
            log_to_gui("トリガーIDが見つかりませんでした")
            return

        # 確認ダイアログ
        if msgbox.askyesno("確認", f"トリガー '{trigger_name}' を削除しますか？"):
            # 汎用削除メソッドを使用
            self.config_manager.delete_trigger_config(self.user_id, broadcaster_id, trigger_id)
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

            # 汎用保存ロジックを使用してトリガー状態を更新
            def update_trigger_enabled(config):
                broadcasters = config.get("broadcasters", {})
                if broadcaster_id in broadcasters:
                    triggers = broadcasters[broadcaster_id].get("triggers", [])
                    for trigger in triggers:
                        if trigger.get("name", "") == trigger_name:
                            current_enabled = trigger.get("enabled", True)
                            new_enabled = not current_enabled
                            trigger["enabled"] = new_enabled
                            return new_enabled
                return None

            result = None
            def wrapper_update(config):
                nonlocal result
                result = update_trigger_enabled(config)
                return result is not None

            if self.config_manager._safe_save_user_config(self.user_id, wrapper_update):
                self.refresh_triggers_list()
                action = "有効" if result else "無効"
                log_to_gui(f"トリガー '{trigger_name}' を{action}にしました")
            else:
                log_to_gui("トリガー設定の更新に失敗しました")

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

        # 汎用保存ロジックを使用して一括更新
        def update_all_triggers_enabled(config):
            broadcasters = config.get("broadcasters", {})
            if broadcaster_id not in broadcasters:
                return False
            triggers = broadcasters[broadcaster_id].get("triggers", [])
            if not triggers:
                return False
            # すべてのトリガーの設定を更新
            for trigger in triggers:
                trigger["enabled"] = enabled
            config["broadcasters"][broadcaster_id]["triggers"] = triggers
            return True

        if self.config_manager._safe_save_user_config(self.user_id, update_all_triggers_enabled):
            self.refresh_triggers_list()
            action = "有効" if enabled else "無効"
            log_to_gui(f"すべてのトリガーを{action}にしました")
        else:
            log_to_gui("トリガー設定の更新に失敗しました")