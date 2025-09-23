import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

from config_manager import HierarchicalConfigManager
from logger import NCVSpecialLogger
from file_monitor import NCVFolderMonitor
from broadcast_detector import BroadcastEndDetector
from pipeline import PipelineExecutor
import bulk_broadcaster_registration
from bulk_broadcaster_registration import show_bulk_registration_dialog

# グローバル変数：メインアプリのインスタンス
main_app_instance = None

def log_to_gui(message):
    """GUIログエリアにメッセージを出力するグローバル関数"""
    if main_app_instance:
        main_app_instance.log_message(message)
    else:
        print(message)  # フォールバック

class NCVSpecialMonitorGUI:
    def __init__(self, root):
        global main_app_instance
        main_app_instance = self

        self.root = root
        self.root.title("NCV Special User Monitor v4")
        self.root.geometry("1000x600")

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
        ttk.Button(buttons_frame, text="配信者管理", command=self.manage_broadcasters).grid(row=0, column=3, padx=(5, 0))

        # 制御ボタン
        control_frame = ttk.Frame(left_frame)
        control_frame.grid(row=4, column=0, pady=(5, 0))

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
        # log_frame.rowconfigure(0, weight=1) を削除 - 縦は固定
        api_frame.columnconfigure(1, weight=1)
        ncv_frame.columnconfigure(1, weight=1)

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
            self.log_message("編集するユーザーを選択してください")
            return

        values = self.users_tree.item(selected[0], "values")
        user_id = values[0]

        dialog = UserEditDialog(self.root, self.config_manager, user_id)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_users_list()

    def remove_special_user(self):
        """ユーザー削除"""
        selected = self.users_tree.selection()
        if not selected:
            self.log_message("編集するユーザーを選択してください")
            return

        values = self.users_tree.item(selected[0], "values")
        user_id = values[0]
        display_name = values[1]

        # 確認なしで削除
        self.config_manager.delete_user_config(user_id)
        self.refresh_users_list()

    def manage_broadcasters(self):
        """配信者管理"""
        selected = self.users_tree.selection()
        if not selected:
            self.log_message("編集するユーザーを選択してください")
            return

        values = self.users_tree.item(selected[0], "values")
        user_id = values[0]
        display_name = values[1]

        dialog = BroadcasterManagementDialog(self.root, self.config_manager, user_id, display_name)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_users_list()

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

            self.config_manager.save_global_config(config)
            # 設定保存の詳細ログ
            special_users = self.config_manager.get_all_special_users()
            user_count = len(special_users)
            self.log_message(f"設定を保存しました - スペシャルユーザー: {user_count}人, NCVフォルダ: {self.ncv_path_var.get()}")

        except Exception as e:
            self.log_message(f"設定保存エラー: {str(e)}")

    def start_monitoring(self):
        """監視開始"""
        try:
            self.save_config()

            # 登録ユーザー情報を取得
            special_users = self.config_manager.get_all_special_users()
            user_count = len(special_users)

            if user_count == 0:
                self.log_message("監視を開始しましたが、スペシャルユーザーが登録されていません")
            else:
                # ユーザー名一覧を作成
                user_names = []
                for user_id, user_config in special_users.items():
                    display_name = user_config.get("display_name", f"ユーザー{user_id}")
                    user_names.append(display_name)

                user_list = ", ".join(user_names[:3])  # 最大3人まで表示
                if user_count > 3:
                    user_list += f" 他{user_count - 3}人"

                self.log_message(f"監視を開始しました - 対象: {user_list} (計{user_count}人)")

            self.file_monitor.start_monitoring()
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

        except Exception as e:
            self.log_message(f"監視開始エラー: {str(e)}")

    def stop_monitoring(self):
        """監視停止"""
        try:
            self.file_monitor.stop_monitoring()
            self.broadcast_detector.stop_all_detections()
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

            # 停止時刻を含めて詳細ログ
            from datetime import datetime
            stop_time = datetime.now().strftime("%H:%M:%S")
            self.log_message(f"監視を停止しました ({stop_time})")

        except Exception as e:
            self.log_message(f"監視停止エラー: {str(e)}")


class UserEditDialog:
    def __init__(self, parent, config_manager, user_id=None):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.user_config = config_manager.get_user_config(user_id) if user_id else config_manager.create_default_user_config("")

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("スペシャルユーザー編集" if user_id else "スペシャルユーザー追加")
        self.dialog.geometry("600x700")
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

        ttk.Label(basic_frame, text="ユーザーID:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.user_id_var = tk.StringVar(value=self.user_config.get("user_id", ""))
        user_id_frame = ttk.Frame(basic_frame)
        user_id_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)
        self.user_id_entry = ttk.Entry(user_id_frame, textvariable=self.user_id_var)
        self.user_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(user_id_frame, text="名前取得", command=self.fetch_user_name).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(basic_frame, text="表示名:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.display_name_var = tk.StringVar(value=self.user_config.get("display_name", ""))
        ttk.Entry(basic_frame, textvariable=self.display_name_var).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)

        basic_frame.columnconfigure(1, weight=1)

        # AI分析設定
        ai_frame = ttk.LabelFrame(main_frame, text="AI分析設定", padding="5")
        ai_frame.pack(fill=tk.X, pady=(0, 10))

        self.analysis_enabled_var = tk.BooleanVar(value=self.user_config.get("ai_analysis", {}).get("enabled", True))
        ttk.Checkbutton(ai_frame, text="AI分析を有効化", variable=self.analysis_enabled_var).pack(anchor=tk.W)

        ttk.Label(ai_frame, text="AIモデル:").pack(anchor=tk.W)
        self.analysis_model_var = tk.StringVar(value=self.user_config.get("ai_analysis", {}).get("model", "openai-gpt4o"))
        ttk.Combobox(ai_frame, textvariable=self.analysis_model_var, values=["openai-gpt4o", "google-gemini-2.5-flash"]).pack(fill=tk.X, pady=2)

        # デフォルト応答設定
        response_frame = ttk.LabelFrame(main_frame, text="デフォルト応答設定", padding="5")
        response_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 応答タイプ
        type_frame = ttk.Frame(response_frame)
        type_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(type_frame, text="応答タイプ:").pack(side=tk.LEFT)
        self.response_type_var = tk.StringVar(value=self.user_config.get("default_response", {}).get("response_type", "predefined"))
        ttk.Radiobutton(type_frame, text="定型メッセージ", variable=self.response_type_var, value="predefined").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(type_frame, text="AI生成", variable=self.response_type_var, value="ai").pack(side=tk.LEFT)

        # メッセージ設定
        msg_frame = ttk.Frame(response_frame)
        msg_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        ttk.Label(msg_frame, text="定型メッセージ (1行1メッセージ):").pack(anchor=tk.W)
        self.messages_text = tk.Text(msg_frame, height=4)
        self.messages_text.pack(fill=tk.BOTH, expand=True)
        messages = self.user_config.get("default_response", {}).get("messages", [])
        self.messages_text.insert("1.0", "\n".join(messages))

        ttk.Label(response_frame, text="AIプロンプト:").pack(anchor=tk.W)
        self.ai_prompt_var = tk.StringVar(value=self.user_config.get("default_response", {}).get("ai_response_prompt", ""))
        ttk.Entry(response_frame, textvariable=self.ai_prompt_var).pack(fill=tk.X, pady=2)

        # 反応設定
        reaction_frame = ttk.Frame(response_frame)
        reaction_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(reaction_frame, text="最大反応回数:").grid(row=0, column=0, sticky=tk.W)
        self.max_reactions_var = tk.StringVar(value=str(self.user_config.get("default_response", {}).get("max_reactions_per_stream", 1)))
        ttk.Entry(reaction_frame, textvariable=self.max_reactions_var, width=10).grid(row=0, column=1, padx=(5, 10))

        ttk.Label(reaction_frame, text="応答遅延(秒):").grid(row=0, column=2, sticky=tk.W)
        self.delay_var = tk.StringVar(value=str(self.user_config.get("default_response", {}).get("response_delay_seconds", 0)))
        ttk.Entry(reaction_frame, textvariable=self.delay_var, width=10).grid(row=0, column=3, padx=(5, 0))

        # スペシャルトリガー管理
        triggers_frame = ttk.LabelFrame(main_frame, text="スペシャルトリガー", padding="5")
        triggers_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(triggers_frame, text="スペシャルトリガー管理", command=self.manage_special_triggers).pack()

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_user).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

    def fetch_user_name(self):
        """ユーザー名取得"""
        user_id = self.user_id_var.get().strip()
        if not user_id:
            self.log_message("ユーザーIDを入力してください")
            return

        try:
            url = f"https://www.nicovideo.jp/user/{user_id}"
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
                self.display_name_var.set(nickname)
                self.log_message(f"ユーザー名を取得しました: {nickname}")
            else:
                self.display_name_var.set(f"ユーザー{user_id}")
                self.log_message("ユーザー名を取得できませんでした")

        except Exception as e:
            self.display_name_var.set(f"ユーザー{user_id}")
            self.log_message(f"ユーザー情報の取得に失敗しました: {str(e)}")

    def manage_special_triggers(self):
        """スペシャルトリガー管理"""
        user_id = self.user_id_var.get().strip()
        if not user_id:
            self.log_message("ユーザーIDを入力してください")
            return

        dialog = SpecialTriggerManagementDialog(self.dialog, self.config_manager, user_id)
        self.dialog.wait_window(dialog.dialog)

    def save_user(self):
        """ユーザー保存"""
        user_id = self.user_id_var.get().strip()
        display_name = self.display_name_var.get().strip()

        if not user_id:
            self.log_message("ユーザーIDを入力してください")
            return
        if not display_name:
            display_name = f"ユーザー{user_id}"

        # メッセージを処理
        messages_text = self.messages_text.get("1.0", tk.END).strip()
        messages = [msg.strip() for msg in messages_text.split("\n") if msg.strip()]
        if not messages:
            messages = [f">>{'{no}'} こんにちは、{display_name}さん"]

        # 設定を作成
        user_config = {
            "user_id": user_id,
            "display_name": display_name,
            "description": "",
            "tags": [],
            "ai_analysis": {
                "enabled": self.analysis_enabled_var.get(),
                "model": self.analysis_model_var.get(),
                "custom_prompt": "",
                "use_default_prompt": True
            },
            "default_response": {
                "response_type": self.response_type_var.get(),
                "messages": messages,
                "ai_response_prompt": self.ai_prompt_var.get(),
                "max_reactions_per_stream": int(self.max_reactions_var.get() or 1),
                "response_delay_seconds": int(self.delay_var.get() or 0)
            },
            "special_triggers": self.user_config.get("special_triggers", []),
            "broadcasters": self.user_config.get("broadcasters", {})
        }

        self.config_manager.save_user_config(user_id, user_config)
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()


class BroadcasterManagementDialog:
    def __init__(self, parent, config_manager, user_id, user_display_name):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.user_display_name = user_display_name

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"配信者管理 - {user_display_name}")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()
        self.refresh_broadcasters_list()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 配信者一覧
        list_frame = ttk.LabelFrame(main_frame, text="配信者一覧", padding="5")
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
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="配信者追加", command=self.add_broadcaster).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="一括登録", command=self.bulk_register_broadcasters).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="一括有効", command=self.enable_all_broadcasters).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="一括無効", command=self.disable_all_broadcasters).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="配信者編集", command=self.edit_broadcaster).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="配信者削除", command=self.delete_broadcaster).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="トリガー管理", command=self.manage_triggers).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(button_frame, text="閉じる", command=self.close_dialog).pack(side=tk.RIGHT)

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
        dialog = BroadcasterEditDialog(self.dialog, self.config_manager, self.user_id)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_broadcasters_list()

    def edit_broadcaster(self):
        """配信者編集"""
        selected = self.broadcasters_tree.selection()
        if not selected:
            self.log_message("編集するユーザーを選択してください")
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
            self.log_message("編集するユーザーを選択してください")
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
            self.log_message("編集するユーザーを選択してください")
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
        self.dialog.geometry("500x400")
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
        response_frame = ttk.LabelFrame(main_frame, text="この配信者でのデフォルト応答設定", padding="5")
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
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_broadcaster).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

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
            self.log_message("編集するユーザーを選択してください")
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
            self.log_message("編集するユーザーを選択してください")
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
        ttk.Entry(detail_frame, textvariable=self.cooldown_var, width=10).grid(row=0, column=5, padx=(5, 0))

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
            "cooldown_minutes": int(self.cooldown_var.get() or 30)
        }

        self.config_manager.save_trigger_config(self.user_id, self.broadcaster_id, trigger_config)
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()


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
            self.log_message("編集するユーザーを選択してください")
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
            self.log_message("編集するユーザーを選択してください")
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
            messagebox.showerror("エラー", f"設定更新エラー: {str(e)}")

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

# 確認なしで一括無効化

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
                "ignore_all_limits": True
            }

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("スペシャルトリガー編集" if trigger_id else "スペシャルトリガー追加")
        self.dialog.geometry("500x500")
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
        self.messages_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        messages = self.trigger_config.get("messages", [])
        self.messages_text.insert("1.0", "\n".join(messages))

        ttk.Label(response_frame, text="AIプロンプト:").pack(anchor=tk.W)
        self.ai_prompt_var = tk.StringVar(value=self.trigger_config.get("ai_response_prompt", ""))
        ttk.Entry(response_frame, textvariable=self.ai_prompt_var).pack(fill=tk.X)

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
            "ignore_all_limits": True
        }

        self.config_manager.save_special_trigger_config(self.user_id, trigger_config)
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()


def main():
    # 必要なディレクトリを作成
    os.makedirs("config", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    root = tk.Tk()
    app = NCVSpecialMonitorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()