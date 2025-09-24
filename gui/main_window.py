"""
NCVSpecialMonitor メインウィンドウ
"""
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import os
import requests
from bs4 import BeautifulSoup
import tempfile
import webbrowser
import time
from datetime import datetime

from config_manager import HierarchicalConfigManager
from logger import NCVSpecialLogger
from file_monitor import NCVFolderMonitor
from broadcast_detector import BroadcastEndDetector
from pipeline import PipelineExecutor
import bulk_broadcaster_registration
from bulk_broadcaster_registration import show_bulk_registration_dialog

from .utils import log_to_gui, set_main_app
from .user_dialog import UserEditDialog
from .broadcaster_dialog import BroadcasterManagementDialog


class NCVSpecialMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NCV Special User Monitor v4")
        self.root.geometry("1000x600")

        # メインアプリのインスタンスを設定
        set_main_app(self)

        # bulk_broadcaster_registrationのlog_to_gui関数を上書き
        bulk_broadcaster_registration.log_to_gui = log_to_gui

        # コンポーネント初期化
        self.config_manager = HierarchicalConfigManager()
        self.logger = NCVSpecialLogger()
        self.pipeline_executor = PipelineExecutor(self.config_manager, self.logger)
        self.broadcast_detector = BroadcastEndDetector(self.config_manager, self.logger, self.pipeline_executor)
        self.file_monitor = NCVFolderMonitor(self.config_manager, self.logger, self.broadcast_detector)

        # パイプラインエグゼキューターにファイルモニターを設定
        self.pipeline_executor.file_monitor = self.file_monitor

        self.setup_gui()
        self.load_config()
        self.root.after(1000, self.update_log_display)

    def update_log_display(self):
        """ログ表示を定期更新（無効化済み - GUIログメッセージが上書きされるのを防ぐ）"""
        # 古いログシステムによる上書きを無効化
        # GUIログメッセージはlog_message()メソッドで直接出力される
        self.root.after(5000, self.update_log_display)

    def log_message(self, message):
        """GUIログエリアにメッセージを出力"""
        try:
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
        except Exception:
            pass

    def setup_gui(self):
        """GUI設定"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 左側のフレーム（設定系）
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # 右側のフレーム（一覧・ログ）
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        # NCVフォルダ設定
        ncv_frame = ttk.LabelFrame(left_frame, text="NCVフォルダ設定", padding="5")
        ncv_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(ncv_frame, text="NCVフォルダパス:").grid(row=0, column=0, sticky=tk.W)
        self.ncv_path_var = tk.StringVar()
        self.ncv_path_entry = ttk.Entry(ncv_frame, textvariable=self.ncv_path_var, width=40)
        self.ncv_path_entry.grid(row=0, column=1, padx=(5, 5), sticky=(tk.W, tk.E))
        ttk.Button(ncv_frame, text="参照", command=self.browse_ncv_folder).grid(row=0, column=2)

        # 監視設定
        monitor_frame = ttk.LabelFrame(left_frame, text="監視設定", padding="5")
        monitor_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        self.monitor_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(monitor_frame, text="監視を有効化", variable=self.monitor_enabled_var).grid(row=0, column=0, sticky=tk.W)

        ttk.Label(monitor_frame, text="チェック間隔(分):").grid(row=1, column=0, sticky=tk.W)
        self.check_interval_var = tk.StringVar()
        ttk.Entry(monitor_frame, textvariable=self.check_interval_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0))

        # API設定
        api_frame = ttk.LabelFrame(left_frame, text="API設定", padding="5")
        api_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        # 分析用AI設定
        ttk.Label(api_frame, text="AI分析モデル:").grid(row=0, column=0, sticky=tk.W)
        self.ai_model_var = tk.StringVar()
        ai_model_combo = ttk.Combobox(api_frame, textvariable=self.ai_model_var, values=["openai-gpt4o", "google-gemini-2.5-flash"])
        ai_model_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        ttk.Label(api_frame, text="OpenAI APIキー:").grid(row=1, column=0, sticky=tk.W)
        self.openai_key_var = tk.StringVar()
        ttk.Entry(api_frame, textvariable=self.openai_key_var, width=50, show="*").grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        ttk.Label(api_frame, text="Google APIキー:").grid(row=2, column=0, sticky=tk.W)
        self.google_key_var = tk.StringVar()
        ttk.Entry(api_frame, textvariable=self.google_key_var, width=50, show="*").grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        # AI反応設定
        ttk.Separator(api_frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(api_frame, text="AI反応モデル:").grid(row=4, column=0, sticky=tk.W)
        self.response_ai_model_var = tk.StringVar()
        response_ai_combo = ttk.Combobox(api_frame, textvariable=self.response_ai_model_var, values=["openai-gpt4o", "google-gemini-2.5-flash"])
        response_ai_combo.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        ttk.Label(api_frame, text="反応用APIキー:").grid(row=5, column=0, sticky=tk.W)
        self.response_api_key_var = tk.StringVar()
        ttk.Entry(api_frame, textvariable=self.response_api_key_var, width=50, show="*").grid(row=5, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        response_settings_frame = ttk.Frame(api_frame)
        response_settings_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(response_settings_frame, text="最大文字数:").grid(row=0, column=0, sticky=tk.W)
        self.max_chars_var = tk.StringVar()
        ttk.Entry(response_settings_frame, textvariable=self.max_chars_var, width=10).grid(row=0, column=1, padx=(5, 10))

        ttk.Label(response_settings_frame, text="分割送信遅延(秒):").grid(row=0, column=2, sticky=tk.W)
        self.split_delay_var = tk.StringVar()
        ttk.Entry(response_settings_frame, textvariable=self.split_delay_var, width=10).grid(row=0, column=3, padx=(5, 0))

        # デフォルト配信者設定
        default_broadcaster_frame = ttk.LabelFrame(left_frame, text="デフォルト配信者設定", padding="5")
        default_broadcaster_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        # ヘルプボタン付きのヘッダー
        header_frame = ttk.Frame(default_broadcaster_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(header_frame, text="デフォルトメッセージ (1行1メッセージ):").pack(side=tk.LEFT)
        ttk.Button(header_frame, text="ヘルプ", command=self.show_broadcaster_help, width=8).pack(side=tk.RIGHT)
        self.default_messages_text = tk.Text(default_broadcaster_frame, height=4, width=50)
        self.default_messages_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(2, 5))

        ttk.Label(default_broadcaster_frame, text="AI応答プロンプト:").grid(row=2, column=0, sticky=tk.W)
        self.default_ai_prompt_var = tk.StringVar()
        ttk.Entry(default_broadcaster_frame, textvariable=self.default_ai_prompt_var, width=50).grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(2, 5))

        settings_frame = ttk.Frame(default_broadcaster_frame)
        settings_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Label(settings_frame, text="最大反応数:").grid(row=0, column=0, sticky=tk.W)
        self.default_max_reactions_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.default_max_reactions_var, width=10).grid(row=0, column=1, padx=(5, 10))

        ttk.Label(settings_frame, text="遅延秒数:").grid(row=0, column=2, sticky=tk.W)
        self.default_response_delay_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.default_response_delay_var, width=10).grid(row=0, column=3, padx=(5, 0))

        # デフォルトユーザー設定
        default_user_frame = ttk.LabelFrame(left_frame, text="デフォルトユーザー設定", padding="5")
        default_user_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 5))

        # ヘルプボタン付きのヘッダー
        user_header_frame = ttk.Frame(default_user_frame)
        user_header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(user_header_frame, text="デフォルトメッセージ (1行1メッセージ):").pack(side=tk.LEFT)
        ttk.Button(user_header_frame, text="ヘルプ", command=self.show_user_help, width=8).pack(side=tk.RIGHT)
        self.default_user_messages_text = tk.Text(default_user_frame, height=4, width=50)
        self.default_user_messages_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(2, 5))

        ttk.Label(default_user_frame, text="AI応答プロンプト:").grid(row=2, column=0, sticky=tk.W)
        self.default_user_ai_prompt_var = tk.StringVar()
        ttk.Entry(default_user_frame, textvariable=self.default_user_ai_prompt_var, width=50).grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(2, 5))

        user_settings_frame = ttk.Frame(default_user_frame)
        user_settings_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Label(user_settings_frame, text="最大反応数:").grid(row=0, column=0, sticky=tk.W)
        self.default_user_max_reactions_var = tk.StringVar()
        ttk.Entry(user_settings_frame, textvariable=self.default_user_max_reactions_var, width=10).grid(row=0, column=1, padx=(5, 10))

        ttk.Label(user_settings_frame, text="遅延秒数:").grid(row=0, column=2, sticky=tk.W)
        self.default_user_response_delay_var = tk.StringVar()
        ttk.Entry(user_settings_frame, textvariable=self.default_user_response_delay_var, width=10).grid(row=0, column=3, padx=(5, 0))

        # スペシャルユーザー設定
        users_frame = ttk.LabelFrame(right_frame, text="スペシャルユーザー設定", padding="5")
        users_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        # ユーザー一覧
        self.users_tree = ttk.Treeview(
            users_frame,
            columns=("user_id", "display_name", "ai_model", "broadcasters", "special_triggers"),
            show="headings",
            height=12
        )
        self.users_tree.heading("user_id", text="ユーザーID")
        self.users_tree.heading("display_name", text="表示名")
        self.users_tree.heading("ai_model", text="AIモデル")
        self.users_tree.heading("broadcasters", text="配信者数")
        self.users_tree.heading("special_triggers", text="スペシャルトリガー数")

        self.users_tree.column("user_id", width=100)
        self.users_tree.column("display_name", width=150)
        self.users_tree.column("ai_model", width=120)
        self.users_tree.column("broadcasters", width=80)
        self.users_tree.column("special_triggers", width=120)

        self.users_tree.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))

        # ダブルクリックイベント
        self.users_tree.bind("<Double-1>", self.on_user_double_click)

        # スクロールバー
        users_scrollbar = ttk.Scrollbar(users_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        users_scrollbar.grid(row=0, column=4, sticky=(tk.N, tk.S))
        self.users_tree.configure(yscrollcommand=users_scrollbar.set)

        # ボタン
        buttons_frame = ttk.Frame(users_frame)
        buttons_frame.grid(row=1, column=0, columnspan=5, pady=(5, 0))

        ttk.Button(buttons_frame, text="ユーザー追加", command=self.add_special_user).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(buttons_frame, text="ユーザー編集", command=self.edit_special_user).grid(row=0, column=1, padx=(5, 5))
        ttk.Button(buttons_frame, text="ユーザー削除", command=self.remove_special_user).grid(row=0, column=2, padx=(5, 5))
        ttk.Button(buttons_frame, text="配信者管理", command=self.manage_broadcasters).grid(row=0, column=3, padx=(5, 5))
        ttk.Button(buttons_frame, text="シリーズ管理", command=self.manage_trigger_series).grid(row=0, column=4, padx=(5, 0))

        # 制御ボタン
        control_frame = ttk.Frame(left_frame)
        control_frame.grid(row=6, column=0, pady=(5, 0))

        self.start_button = ttk.Button(control_frame, text="監視開始", command=self.start_monitoring)
        self.start_button.grid(row=0, column=0, padx=(0, 5))

        self.stop_button = ttk.Button(control_frame, text="監視停止", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(5, 5))

        ttk.Button(control_frame, text="設定保存", command=self.save_config).grid(row=0, column=2, padx=(5, 0))

        # ログ
        log_frame = ttk.LabelFrame(right_frame, text="ログ", padding="5")
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        self.log_text = tk.Text(log_frame, height=8)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        # グリッド設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # メインフレーム - 左右分割
        main_frame.columnconfigure(0, weight=0)  # 左側（設定）は固定幅
        main_frame.columnconfigure(1, weight=1)  # 右側（一覧・ログ）は伸縮
        main_frame.rowconfigure(0, weight=1)

        # 左側フレーム
        left_frame.columnconfigure(0, weight=1)

        # 右側フレーム
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)  # ユーザー一覧だけが伸縮
        right_frame.rowconfigure(1, weight=0)  # ログは固定サイズ

        # 個別フレーム
        users_frame.columnconfigure(0, weight=1)
        users_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)  # 横幅だけ伸縮
        api_frame.columnconfigure(1, weight=1)
        ncv_frame.columnconfigure(1, weight=1)
        default_broadcaster_frame.columnconfigure(0, weight=1)

    def browse_ncv_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.ncv_path_var.set(folder)

    def load_config(self):
        """設定を読み込み"""
        config = self.config_manager.load_global_config()

        # 基本設定
        self.ncv_path_var.set(config.get("ncv_folder_path", ""))
        self.monitor_enabled_var.set(config.get("monitor_enabled", True))
        self.check_interval_var.set(str(config.get("check_interval_minutes", 5)))

        # API設定
        api_settings = config.get("api_settings", {})
        self.ai_model_var.set(api_settings.get("summary_ai_model", "openai-gpt4o"))
        self.openai_key_var.set(api_settings.get("openai_api_key", ""))
        self.google_key_var.set(api_settings.get("google_api_key", ""))

        # AI反応設定
        self.response_ai_model_var.set(api_settings.get("response_ai_model", "openai-gpt4o"))
        self.response_api_key_var.set(api_settings.get("response_api_key", ""))
        self.max_chars_var.set(str(api_settings.get("response_max_characters", 100)))
        self.split_delay_var.set(str(api_settings.get("response_split_delay_seconds", 1)))

        # デフォルト配信者設定
        default_broadcaster = config.get("default_broadcaster_config", {})
        default_messages = default_broadcaster.get("messages", [])
        self.default_messages_text.delete(1.0, tk.END)
        self.default_messages_text.insert(1.0, "\n".join(default_messages))

        self.default_ai_prompt_var.set(default_broadcaster.get("ai_response_prompt", "{{broadcaster_name}}の配信に特化した親しみやすい返答をしてください"))
        self.default_max_reactions_var.set(str(default_broadcaster.get("max_reactions_per_stream", 1)))
        self.default_response_delay_var.set(str(default_broadcaster.get("response_delay_seconds", 0)))

        # デフォルトユーザー設定
        default_user = config.get("default_user_config", {})
        default_user_messages = default_user.get("default_response", {}).get("messages", [])
        self.default_user_messages_text.delete(1.0, tk.END)
        self.default_user_messages_text.insert(1.0, "\n".join(default_user_messages))

        default_response = default_user.get("default_response", {})
        self.default_user_ai_prompt_var.set(default_response.get("ai_response_prompt", "{{display_name}}として親しみやすく挨拶してください"))
        self.default_user_max_reactions_var.set(str(default_response.get("max_reactions_per_stream", 1)))
        self.default_user_response_delay_var.set(str(default_response.get("response_delay_seconds", 0)))

        # ユーザー一覧を更新
        self.refresh_users_list()

    def refresh_users_list(self):
        """ユーザー一覧を更新"""
        # 既存の項目をクリア
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)

        # ユーザーを取得して表示
        users = self.config_manager.get_all_special_users()
        for user_id, user_config in users.items():
            display_name = user_config.get("display_name", f"ユーザー{user_id}")
            ai_model = user_config.get("ai_analysis", {}).get("model", "openai-gpt4o")
            broadcasters_count = len(user_config.get("broadcasters", {}))
            special_triggers_count = len(user_config.get("special_triggers", []))

            self.users_tree.insert(
                "",
                tk.END,
                values=(
                    user_id,
                    display_name,
                    ai_model,
                    f"{broadcasters_count}個",
                    f"{special_triggers_count}個"
                )
            )

    def add_special_user(self):
        """ユーザー追加"""
        dialog = UserEditDialog(self.root, self.config_manager)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_users_list()

    def edit_special_user(self):
        """ユーザー編集"""
        selected = self.users_tree.selection()
        if not selected:
            log_to_gui("編集するユーザーを選択してください")
            return

        values = self.users_tree.item(selected[0], "values")
        user_id = values[0]

        dialog = UserEditDialog(self.root, self.config_manager, user_id)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_users_list()

    def on_user_double_click(self, event):
        """ユーザー一覧ダブルクリック処理 - ユーザー編集画面を開く"""
        selected = self.users_tree.selection()
        if selected:
            self.edit_special_user()

    def remove_special_user(self):
        """ユーザー削除"""
        selected = self.users_tree.selection()
        if not selected:
            log_to_gui("編集するユーザーを選択してください")
            return

        values = self.users_tree.item(selected[0], "values")
        user_id = values[0]
        display_name = values[1]

        # 確認ダイアログを表示
        from tkinter import messagebox
        result = messagebox.askyesno(
            "ユーザー削除の確認",
            f"ユーザー「{display_name}」(ID: {user_id})を削除しますか？\n\n"
            f"この操作により、以下のデータが完全に削除されます：\n"
            f"• ユーザー設定\n"
            f"• 配信者設定\n"
            f"• トリガー設定\n"
            f"• スペシャルトリガー設定\n\n"
            f"この操作は取り消すことができません。",
            icon='warning'
        )

        if result:
            try:
                self.config_manager.delete_user_config(user_id)
                self.refresh_users_list()
                log_to_gui(f"ユーザー「{display_name}」を削除しました")
            except Exception as e:
                log_to_gui(f"ユーザー削除エラー: {str(e)}")
                messagebox.showerror("削除エラー", f"ユーザーの削除に失敗しました:\n{str(e)}")
        else:
            log_to_gui("ユーザー削除をキャンセルしました")

    def manage_broadcasters(self):
        """配信者管理"""
        selected = self.users_tree.selection()
        if not selected:
            log_to_gui("編集するユーザーを選択してください")
            return

        values = self.users_tree.item(selected[0], "values")
        user_id = values[0]
        display_name = values[1]

        dialog = BroadcasterManagementDialog(self.root, self.config_manager, user_id, display_name)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_users_list()

    def manage_trigger_series(self):
        """トリガーシリーズ管理"""
        from .trigger_series_dialog import TriggerSeriesManagementDialog
        dialog = TriggerSeriesManagementDialog(self.root, self.config_manager)
        self.root.wait_window(dialog.dialog)

    def save_config(self):
        """設定保存"""
        try:
            config = self.config_manager.load_global_config()

            # 基本設定
            config["ncv_folder_path"] = self.ncv_path_var.get()
            config["monitor_enabled"] = self.monitor_enabled_var.get()
            config["check_interval_minutes"] = int(self.check_interval_var.get() or 5)

            # API設定
            api_settings = config.get("api_settings", {})
            api_settings["summary_ai_model"] = self.ai_model_var.get()
            api_settings["openai_api_key"] = self.openai_key_var.get()
            api_settings["google_api_key"] = self.google_key_var.get()

            # AI反応設定
            api_settings["response_ai_model"] = self.response_ai_model_var.get()
            api_settings["response_api_key"] = self.response_api_key_var.get()
            api_settings["response_max_characters"] = int(self.max_chars_var.get() or 100)
            api_settings["response_split_delay_seconds"] = int(self.split_delay_var.get() or 1)

            config["api_settings"] = api_settings

            # デフォルト配信者設定
            messages_text = self.default_messages_text.get(1.0, tk.END).strip()
            default_messages = [line.strip() for line in messages_text.split("\n") if line.strip()]

            config["default_broadcaster_config"] = {
                "response_type": "predefined",
                "messages": default_messages,
                "ai_response_prompt": self.default_ai_prompt_var.get(),
                "max_reactions_per_stream": int(self.default_max_reactions_var.get() or 1),
                "response_delay_seconds": int(self.default_response_delay_var.get() or 0)
            }

            # デフォルトユーザー設定
            user_messages_text = self.default_user_messages_text.get(1.0, tk.END).strip()
            default_user_messages = [line.strip() for line in user_messages_text.split("\n") if line.strip()]

            config["default_user_config"] = {
                "description": "{{display_name}}さんの監視設定",
                "default_response": {
                    "response_type": "predefined",
                    "messages": default_user_messages,
                    "ai_response_prompt": self.default_user_ai_prompt_var.get(),
                    "max_reactions_per_stream": int(self.default_user_max_reactions_var.get() or 1),
                    "response_delay_seconds": int(self.default_user_response_delay_var.get() or 0)
                }
            }

            self.config_manager.save_global_config(config)
            # 設定保存の詳細ログ
            special_users = self.config_manager.get_all_special_users()
            user_count = len(special_users)
            log_to_gui(f"設定を保存しました - スペシャルユーザー: {user_count}人, NCVフォルダ: {self.ncv_path_var.get()}")

        except Exception as e:
            log_to_gui(f"設定保存エラー: {str(e)}")

    def start_monitoring(self):
        """監視開始"""
        try:
            self.save_config()

            # 登録ユーザー情報を取得
            special_users = self.config_manager.get_all_special_users()
            user_count = len(special_users)

            if user_count == 0:
                log_to_gui("監視を開始しましたが、スペシャルユーザーが登録されていません")
            else:
                # ユーザー名一覧を作成
                user_names = []
                for user_id, user_config in special_users.items():
                    display_name = user_config.get("display_name", f"ユーザー{user_id}")
                    user_names.append(display_name)

                    log_to_gui(f"監視を開始しました - {user_count}人のスペシャルユーザーを監視: {', '.join(user_names[:3])}{'...' if len(user_names) > 3 else ''}")

            self.file_monitor.start_monitoring()
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

        except Exception as e:
            log_to_gui(f"監視開始エラー: {str(e)}")

    def stop_monitoring(self):
        """監視停止"""
        try:
            self.file_monitor.stop_monitoring()
            log_to_gui("監視を停止しました")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
        except Exception as e:
            log_to_gui(f"監視停止エラー: {str(e)}")

    def show_broadcaster_help(self):
        """配信者設定のヘルプ表示"""
        help_text = """【配信者設定ヘルプ】

デフォルトメッセージ:
- 1行につき1つのメッセージを記入
- 配信開始時にランダムで選ばれます
- 空行は無視されます

AI応答プロンプト:
- AIが自動で反応する際の指示
- {{broadcaster_name}} で配信者名を置換
- 例: "{{broadcaster_name}}の配信を楽しんでいるファンとして反応してください"

設定値:
- 最大反応数: 1配信あたりの最大反応回数
- 遅延秒数: メッセージ送信前の待機時間

※これらはデフォルト値です。個別設定で上書きできます。"""

        # ヘルプウィンドウを作成
        help_window = tk.Toplevel(self.root)
        help_window.title("配信者設定ヘルプ")
        help_window.geometry("500x300")
        help_window.resizable(True, True)

        # テキスト表示
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

        # 閉じるボタン
        button_frame = ttk.Frame(help_window)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="閉じる", command=help_window.destroy).pack()

    def show_user_help(self):
        """ユーザー設定のヘルプ表示"""
        help_text = """【ユーザー設定ヘルプ】

デフォルトメッセージ:
- 1行につき1つのメッセージを記入
- ユーザーが配信開始時にランダムで選ばれます
- 空行は無視されます

AI応答プロンプト:
- AIが自動で反応する際の指示
- {{display_name}} でユーザー表示名を置換
- 例: "{{display_name}}として親しみやすく挨拶してください"

設定値:
- 最大反応数: 1配信あたりの最大反応回数
- 遅延秒数: メッセージ送信前の待機時間

※これらはデフォルト値です。個別ユーザー設定で上書きできます。"""

        # ヘルプウィンドウを作成
        help_window = tk.Toplevel(self.root)
        help_window.title("ユーザー設定ヘルプ")
        help_window.geometry("500x300")
        help_window.resizable(True, True)

        # テキスト表示
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

        # 閉じるボタン
        button_frame = ttk.Frame(help_window)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="閉じる", command=help_window.destroy).pack()