import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

from config_manager import NCVSpecialConfigManager
from logger import NCVSpecialLogger
from file_monitor import NCVFolderMonitor
from broadcast_detector import BroadcastEndDetector
from pipeline import PipelineExecutor
from config_manager import IndividualConfigManager

class NCVSpecialMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NCV Special User Monitor")
        self.root.geometry("800x600")

        # コンポーネント初期化
        self.config_manager = IndividualConfigManager()
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
        """ログ表示を定期更新"""
        try:
            recent_logs = self.logger.get_recent_logs(20)  # 最新20行
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, recent_logs)
            self.log_text.see(tk.END)
        except Exception:
            pass
        # 5秒後に再実行
        self.root.after(5000, self.update_log_display)

    def setup_gui(self):
        """GUI設定"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # NCVフォルダ設定
        ncv_frame = ttk.LabelFrame(main_frame, text="NCVフォルダ設定", padding="5")
        ncv_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(ncv_frame, text="NCVフォルダパス:").grid(row=0, column=0, sticky=tk.W)
        self.ncv_path_var = tk.StringVar()
        self.ncv_path_entry = ttk.Entry(ncv_frame, textvariable=self.ncv_path_var, width=60)
        self.ncv_path_entry.grid(row=0, column=1, padx=(5, 5))
        ttk.Button(ncv_frame, text="参照", command=self.browse_ncv_folder).grid(row=0, column=2)

        # 監視設定
        monitor_frame = ttk.LabelFrame(main_frame, text="監視設定", padding="5")
        monitor_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.monitor_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(monitor_frame, text="監視を有効化", variable=self.monitor_enabled_var).grid(row=0, column=0, sticky=tk.W)

        ttk.Label(monitor_frame, text="チェック間隔(分):").grid(row=1, column=0, sticky=tk.W)
        self.check_interval_var = tk.StringVar()
        ttk.Entry(monitor_frame, textvariable=self.check_interval_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0))

        # API設定
        api_frame = ttk.LabelFrame(main_frame, text="API設定", padding="5")
        api_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

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

        # スペシャルユーザー設定
        users_frame = ttk.LabelFrame(main_frame, text="スペシャルユーザー設定", padding="5")
        users_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # ★★★★★ 重要：prompt_value（隠し列）を追加して実データを保持する ★★★★★
        self.users_tree = ttk.Treeview(
            users_frame,
            columns=("user_id", "display_name", "ai_model", "custom_prompt", "comment_system", "prompt_value"),
            show="headings",
            height=8
        )
        self.users_tree.heading("user_id", text="ユーザーID")
        self.users_tree.heading("display_name", text="表示名")
        self.users_tree.heading("ai_model", text="AIモデル")
        self.users_tree.heading("custom_prompt", text="カスタムプロンプト")
        self.users_tree.heading("comment_system", text="コメントシステム")
        # 隠し列（実データ保持用）
        self.users_tree.heading("prompt_value", text="prompt_value")
        self.users_tree.column("user_id", width=100)
        self.users_tree.column("display_name", width=150)
        self.users_tree.column("ai_model", width=120)
        self.users_tree.column("custom_prompt", width=100)
        self.users_tree.column("comment_system", width=100)
        self.users_tree.column("prompt_value", width=0, stretch=False)  # 非表示
        self.users_tree.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))

        ttk.Button(users_frame, text="ユーザー追加", command=self.add_special_user).grid(row=1, column=0, pady=(5, 0), padx=(0, 5))
        ttk.Button(users_frame, text="ユーザー編集", command=self.edit_special_user).grid(row=1, column=1, pady=(5, 0), padx=(5, 5))
        ttk.Button(users_frame, text="ユーザー削除", command=self.remove_special_user).grid(row=1, column=2, pady=(5, 0), padx=(5, 0))

        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))

        self.start_button = ttk.Button(control_frame, text="監視開始", command=self.start_monitoring)
        self.start_button.grid(row=0, column=0, padx=(0, 5))

        self.stop_button = ttk.Button(control_frame, text="監視停止", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(5, 5))

        ttk.Button(control_frame, text="設定保存", command=self.save_config).grid(row=0, column=2, padx=(5, 0))

        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))

        self.log_text = tk.Text(log_frame, height=10)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(5, weight=1)
        users_frame.columnconfigure(0, weight=1)
        users_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def browse_ncv_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.ncv_path_var.set(folder)

    def add_special_user(self):
        dialog = UserEditDialog(self.root)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            user_data = dialog.result
            comment_status = "有効" if user_data.get("comment_system_enabled", True) else "無効"
            self.users_tree.insert(
                "",
                tk.END,
                values=(
                    user_data["user_id"],
                    user_data["display_name"],
                    user_data["analysis_ai_model"],
                    "設定済み" if user_data.get("analysis_prompt", "").strip() else "デフォルト",
                    comment_status,
                    user_data.get("analysis_prompt", "")
                )
            )

    def edit_special_user(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "編集するユーザーを選択してください")
            return
        values = self.users_tree.item(selected[0], "values")
        user_id = values[0]

        # 既存設定をロードしてダイアログに渡す
        config = self.config_manager.load_config()
        users = config.get("special_users_config", {}).get("users", {})
        user_config = users.get(user_id, {})
        # TreeView の prompt_value が最新なので上書きして渡す
        if len(values) >= 6:
            user_config = {**user_config, "analysis_prompt": values[5]}

        dialog = UserEditDialog(self.root, user_config)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            user_data = dialog.result
            comment_status = "有効" if user_data.get("comment_system_enabled", True) else "無効"
            self.users_tree.item(
                selected[0],
                values=(
                    user_data["user_id"],
                    user_data["display_name"],
                    user_data["analysis_ai_model"],
                    "設定済み" if user_data.get("analysis_prompt", "").strip() else "デフォルト",
                    comment_status,
                    user_data.get("analysis_prompt", "")
                )
            )

    def remove_special_user(self):
        selected = self.users_tree.selection()
        if selected:
            self.users_tree.delete(selected)

    def load_config(self):
        config = self.config_manager.load_config()
        self.ncv_path_var.set(config.get("ncv_folder_path", ""))
        self.monitor_enabled_var.set(config.get("monitor_enabled", True))
        self.check_interval_var.set(str(config.get("check_interval_minutes", 5)))
        api_settings = config.get("api_settings", {})
        self.ai_model_var.set(api_settings.get("summary_ai_model", "openai-gpt4o"))
        self.openai_key_var.set(api_settings.get("openai_api_key", ""))
        self.google_key_var.set(api_settings.get("google_api_key", ""))

        special_users_config = config.get("special_users_config", {})
        users = special_users_config.get("users", {})

        # 一旦クリア
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)

        # JSON -> TreeView（prompt_value も入れる）
        for user_id, user_config in users.items():
            display_name = user_config.get("display_name", f"ユーザー{user_id}")
            ai_model = user_config.get("analysis_ai_model", "openai-gpt4o")
            prompt_value = user_config.get("analysis_prompt", "")
            has_custom_prompt = bool(prompt_value)
            comment_status = "有効" if user_config.get("comment_system_enabled", True) else "無効"
            self.users_tree.insert(
                "",
                tk.END,
                values=(
                    user_id,
                    display_name,
                    ai_model,
                    "設定済み" if has_custom_prompt else "デフォルト",
                    comment_status,
                    prompt_value
                )
            )

    def save_config(self, silent=False):
        """TreeViewから直接 prompt_value を取得して保存（silent=True ならポップアップ非表示）"""
        try:
            config = self.config_manager.load_config()
            config["ncv_folder_path"] = self.ncv_path_var.get()
            config["monitor_enabled"] = self.monitor_enabled_var.get()
            config["check_interval_minutes"] = int(self.check_interval_var.get() or 5)
            config["api_settings"]["summary_ai_model"] = self.ai_model_var.get()
            config["api_settings"]["openai_api_key"] = self.openai_key_var.get()
            config["api_settings"]["google_api_key"] = self.google_key_var.get()

            existing_users = config.get("special_users_config", {}).get("users", {})
            default_prompt = config.get("special_users_config", {}).get("default_analysis_prompt", "")
            current_tree_users = {}

            for item in self.users_tree.get_children():
                values = self.users_tree.item(item, "values")
                if len(values) < 6:
                    user_id = values[0]
                    display_name = values[1] if len(values) > 1 else f"ユーザー{user_id}"
                    ai_model = values[2] if len(values) > 2 else "openai-gpt4o"
                    comment_status = values[4] if len(values) > 4 else "有効"
                    prompt_value = ""
                else:
                    user_id, display_name, ai_model, _, comment_status, prompt_value = values

                base = existing_users.get(user_id, {
                    "user_id": user_id,
                    "analysis_enabled": True,
                    "template": "user_detail.html",
                    "description": "",
                    "tags": [],
                    "comment_system_enabled": True,
                    "send_messages": [f">>{'{no}'} こんにちは、{display_name}さん"],
                    "trigger_enabled": True,
                    "trigger_type": "first_comment",
                    "keywords": ["こんにちは", "初見"],
                    "max_reactions_per_stream": 1,
                    "cooldown_minutes": 30,
                    "owner_id_overrides": {}
                }).copy()

                base["display_name"] = display_name
                base["analysis_ai_model"] = ai_model
                base["analysis_prompt"] = (prompt_value or "").strip() or default_prompt
                base["comment_system_enabled"] = comment_status == "有効"

                current_tree_users[user_id] = base

                # ✅ 個別ユーザー設定も保存
                self.config_manager.save_user_config(
                    user_id=user_id,
                    display_name=display_name,
                    config={
                        "user_info": {
                            "user_id": user_id,
                            "display_name": display_name,
                            "description": base.get("description", ""),
                            "tags": base.get("tags", [])
                        },
                        "ai_analysis": {
                            "enabled": base.get("analysis_enabled", True),
                            "model": ai_model,
                            "custom_prompt": prompt_value.strip(),
                            "use_default_prompt": not bool(prompt_value.strip())
                        },
                        "comment_system": base.get("comment_system", {}),
                        "template_settings": {
                            "template": base.get("template", "user_detail.html")
                        },
                        "metadata": {
                            "created_at": base.get("metadata", {}).get("created_at", datetime.now().isoformat()),
                            "updated_at": datetime.now().isoformat(),
                            "config_version": "2.0"
                        }
                    }
                )

            if "special_users_config" not in config:
                config["special_users_config"] = {}
            config["special_users_config"]["users"] = current_tree_users

            self.config_manager.save_config(config)

            self.logger.info(f"設定保存成功: {len(current_tree_users)} ユーザーを保存しました")
            for uid, cfg in current_tree_users.items():
                preview = (cfg.get("analysis_prompt", "")[:50]).replace("\n", "\\n")
                self.logger.info(f"[SAVE] {uid}: '{preview}'...")

            if not silent:
                messagebox.showinfo("成功", "設定を保存しました")

        except Exception as e:
            self.logger.error(f"設定保存エラー: {str(e)}")
            messagebox.showerror("エラー", f"設定保存エラー: {str(e)}")



    def start_monitoring(self):
        try:
            self.save_config(silent=True)  # ← ポップアップを抑制
            self.file_monitor.start_monitoring()

            # ★ テスト用：5秒後に状況を確認
            # def check_status():
            #     monitor_status = self.file_monitor.get_monitoring_status()
            #     detector_status = self.broadcast_detector.get_detection_status()
            #     print(f"監視状況: {monitor_status}")
            #     print(f"検出状況: {detector_status}")
            #     self.root.after(5000, check_status)

            # self.root.after(5000, check_status)

            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, "監視を開始しました\n")
            self.log_text.see(tk.END)
        except Exception as e:
            messagebox.showerror("エラー", f"監視開始エラー: {str(e)}")

    def stop_monitoring(self):
        try:
            self.file_monitor.stop_monitoring()
            self.broadcast_detector.stop_all_detections()
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.log_text.insert(tk.END, "監視を停止しました\n")
            self.log_text.see(tk.END)
        except Exception as e:
            messagebox.showerror("エラー", f"監視停止エラー: {str(e)}")


class UserEditDialog:
    def __init__(self, parent, user_config=None):
        self.result = None
        self.user_config = user_config or {}
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("スペシャルユーザー編集" if user_config else "スペシャルユーザー追加")
        self.dialog.geometry("700x800")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Notebookでタブ分割
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 基本設定タブ
        basic_frame = ttk.Frame(notebook, padding="10")
        notebook.add(basic_frame, text="基本設定")
        self.setup_basic_tab(basic_frame)

        # コメントシステムタブ
        comment_frame = ttk.Frame(notebook, padding="10")
        notebook.add(comment_frame, text="コメントシステム")
        self.setup_comment_tab(comment_frame)

        # 高度な設定タブ
        advanced_frame = ttk.Frame(notebook, padding="10")
        notebook.add(advanced_frame, text="高度な設定")
        self.setup_advanced_tab(advanced_frame)

        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="保存", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)

        if not user_config:
            self.user_id_entry.focus()

    def setup_basic_tab(self, frame):
        """基本設定タブのセットアップ"""
        ttk.Label(frame, text="ユーザーID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.user_id_var = tk.StringVar(value=self.user_config.get("user_id", ""))
        user_id_frame = ttk.Frame(frame)
        user_id_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.user_id_entry = ttk.Entry(user_id_frame, textvariable=self.user_id_var, width=20)
        self.user_id_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.fetch_button = ttk.Button(user_id_frame, text="名前取得", command=self.fetch_user_name)
        self.fetch_button.grid(row=0, column=1, padx=(5, 0))

        ttk.Label(frame, text="表示名:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.display_name_var = tk.StringVar(value=self.user_config.get("display_name", ""))
        ttk.Entry(frame, textvariable=self.display_name_var, width=35).grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(frame, text="AIモデル:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.ai_model_var = tk.StringVar(value=self.user_config.get("analysis_ai_model", "openai-gpt4o"))
        ai_model_combo = ttk.Combobox(frame, textvariable=self.ai_model_var, values=["openai-gpt4o", "google-gemini-2.5-flash"])
        ai_model_combo.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.analysis_enabled_var = tk.BooleanVar(value=self.user_config.get("analysis_enabled", True))
        ttk.Checkbutton(frame, text="AI分析を有効化", variable=self.analysis_enabled_var).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(frame, text="カスタムプロンプト:").grid(row=4, column=0, padx=5, pady=5, sticky=(tk.W, tk.N))
        prompt_frame = ttk.Frame(frame)
        prompt_frame.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.prompt_text = tk.Text(prompt_frame, height=10, width=50)
        self.prompt_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        prompt_scrollbar = ttk.Scrollbar(prompt_frame, orient=tk.VERTICAL, command=self.prompt_text.yview)
        prompt_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.prompt_text.configure(yscrollcommand=prompt_scrollbar.set)

        default_prompt = (
            "以下のユーザーのコメント履歴を分析して、このユーザーの特徴、傾向、配信との関わり方について詳しく分析してください。\n\n"
            "分析観点：\n"
            "- コメントの頻度と投稿タイミング\n"
            "- コメント内容の傾向（質問、感想、ツッコミなど）\n"
            "- 配信者との関係性\n"
            "- 他の視聴者との関わり\n"
            "- このユーザーの配信に対する貢献度\n"
            "- 特徴的な発言や行動パターン"
        )
        current_prompt = self.user_config.get("analysis_prompt", default_prompt)
        if not (current_prompt or "").strip():
            current_prompt = default_prompt
        self.prompt_text.insert("1.0", current_prompt)

        ttk.Label(frame, text="説明・メモ:").grid(row=5, column=0, padx=5, pady=5, sticky=(tk.W, tk.N))
        self.description_text = tk.Text(frame, height=3, width=50)
        self.description_text.grid(row=5, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.description_text.insert("1.0", self.user_config.get("description", ""))

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(4, weight=1)
        user_id_frame.columnconfigure(0, weight=1)
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)

    def setup_comment_tab(self, frame):
        """コメントシステムタブのセットアップ"""
        self.comment_enabled_var = tk.BooleanVar(value=self.user_config.get("comment_system_enabled", True))
        ttk.Checkbutton(frame, text="コメントシステムを有効化", variable=self.comment_enabled_var).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)

        # 送信メッセージ設定
        ttk.Label(frame, text="送信メッセージ:").grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.N))
        ttk.Label(frame, text="(1行につき1メッセージ、ランダムに選択されます)", font=("", 8)).grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5)

        messages_frame = ttk.Frame(frame)
        messages_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.messages_text = tk.Text(messages_frame, height=6, width=60)
        self.messages_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        messages_scrollbar = ttk.Scrollbar(messages_frame, orient=tk.VERTICAL, command=self.messages_text.yview)
        messages_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.messages_text.configure(yscrollcommand=messages_scrollbar.set)

        # デフォルトメッセージを設定
        send_messages = self.user_config.get("send_messages", [])
        if not send_messages:
            display_name = self.user_config.get("display_name", "")
            send_messages = [f">>{'{no}'} こんにちは、{display_name}さん"]
        self.messages_text.insert("1.0", "\n".join(send_messages))

        # トリガー設定
        trigger_frame = ttk.LabelFrame(frame, text="トリガー設定", padding="5")
        trigger_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=10)

        self.trigger_enabled_var = tk.BooleanVar(value=self.user_config.get("trigger_enabled", True))
        ttk.Checkbutton(trigger_frame, text="トリガーを有効化", variable=self.trigger_enabled_var).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=2)

        ttk.Label(trigger_frame, text="トリガータイプ:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.trigger_type_var = tk.StringVar(value=self.user_config.get("trigger_type", "first_comment"))
        trigger_combo = ttk.Combobox(trigger_frame, textvariable=self.trigger_type_var,
                                   values=["first_comment", "keyword", "always"], state="readonly")
        trigger_combo.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)

        ttk.Label(trigger_frame, text="キーワード:").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(trigger_frame, text="(カンマ区切り)", font=("", 8)).grid(row=3, column=0, padx=5, sticky=tk.W)
        self.keywords_var = tk.StringVar(value=", ".join(self.user_config.get("keywords", ["こんにちは", "初見"])))
        ttk.Entry(trigger_frame, textvariable=self.keywords_var, width=40).grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)

        ttk.Label(trigger_frame, text="配信あたり最大反応回数:").grid(row=4, column=0, padx=5, pady=2, sticky=tk.W)
        self.max_reactions_var = tk.StringVar(value=str(self.user_config.get("max_reactions_per_stream", 1)))
        max_reactions_frame = ttk.Frame(trigger_frame)
        max_reactions_frame.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
        ttk.Entry(max_reactions_frame, textvariable=self.max_reactions_var, width=10).grid(row=0, column=0)
        ttk.Label(max_reactions_frame, text="(-1で無制限)", font=("", 8)).grid(row=0, column=1, padx=(5,0))

        ttk.Label(trigger_frame, text="クールダウン(分):").grid(row=5, column=0, padx=5, pady=2, sticky=tk.W)
        self.cooldown_var = tk.StringVar(value=str(self.user_config.get("cooldown_minutes", 30)))
        ttk.Entry(trigger_frame, textvariable=self.cooldown_var, width=10).grid(row=5, column=1, sticky=tk.W, padx=5, pady=2)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)
        trigger_frame.columnconfigure(1, weight=1)
        messages_frame.columnconfigure(0, weight=1)
        messages_frame.rowconfigure(0, weight=1)

    def setup_advanced_tab(self, frame):
        """高度な設定タブのセットアップ"""
        ttk.Label(frame, text="配信者ID別設定 (JSON形式):", font=("", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(frame, text="特定の配信者での動作を個別に設定できます", font=("", 8)).grid(row=1, column=0, padx=5, sticky=tk.W)

        overrides_frame = ttk.Frame(frame)
        overrides_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.overrides_text = tk.Text(overrides_frame, height=15, width=70)
        self.overrides_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        overrides_scrollbar = ttk.Scrollbar(overrides_frame, orient=tk.VERTICAL, command=self.overrides_text.yview)
        overrides_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.overrides_text.configure(yscrollcommand=overrides_scrollbar.set)

        # デフォルトのoverrides例を表示
        overrides = self.user_config.get("owner_id_overrides", {})
        if not overrides:
            overrides = {
                "lv0001": {
                    "send_messages": [f">>{'{no}'} 特別対応：{self.user_config.get('display_name', '')}さん（lv0001）！✨"],
                    "trigger_conditions": {
                        "trigger_type": "always",
                        "max_reactions_per_stream": 3
                    }
                }
            }

        import json
        self.overrides_text.insert("1.0", json.dumps(overrides, ensure_ascii=False, indent=2))

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        overrides_frame.columnconfigure(0, weight=1)
        overrides_frame.rowconfigure(0, weight=1)

    def fetch_user_name(self):
        user_id = self.user_id_var.get().strip()
        if not user_id:
            messagebox.showwarning("警告", "ユーザーIDを入力してください")
            return
        try:
            self.fetch_button.config(state=tk.DISABLED, text="取得中...")
            self.dialog.update()
            url = f"https://www.nicovideo.jp/user/{user_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            nickname = None
            # 1. metaタグ
            meta_tag = soup.find("meta", {"property": "profile:username"})
            if meta_tag and meta_tag.get("content"):
                nickname = meta_tag["content"]
            # 2. JSON-LD
            if not nickname:
                json_ld = soup.find("script", type="application/ld+json")
                if json_ld:
                    try:
                        data = json.loads(json_ld.string)
                        if isinstance(data, dict) and "name" in data:
                            nickname = data["name"]
                    except json.JSONDecodeError:
                        pass
            # 3. クラス名検索
            if not nickname:
                element = soup.find(class_="UserDetailsHeader-nickname")
                if element:
                    nickname = element.get_text(strip=True)

            if nickname:
                self.display_name_var.set(nickname)
                messagebox.showinfo("成功", f"ユーザー名を取得しました: {nickname}")
            else:
                self.display_name_var.set(f"ユーザー{user_id}")
                messagebox.showwarning("警告", "ユーザー名を取得できませんでした。手動で入力してください。")
        except requests.RequestException as e:
            self.display_name_var.set(f"ユーザー{user_id}")
            messagebox.showerror("エラー", f"ユーザー情報の取得に失敗しました: {str(e)}")
        finally:
            self.fetch_button.config(state=tk.NORMAL, text="名前取得")

    def ok_clicked(self):
        user_id = self.user_id_var.get().strip()
        display_name = self.display_name_var.get().strip()
        if not user_id:
            messagebox.showerror("エラー", "ユーザーIDを入力してください")
            return
        if not display_name:
            display_name = f"ユーザー{user_id}"

        prompt_value = (self.prompt_text.get("1.0", tk.END) or "").strip()
        if not prompt_value:
            prompt_value = (
                "以下のユーザーのコメント履歴を分析して、このユーザーの特徴、傾向、配信との関わり方について詳しく分析してください。\n\n"
                "分析観点：\n"
                "- コメントの頻度と投稿タイミング\n"
                "- コメント内容の傾向（質問、感想、ツッコミなど）\n"
                "- 配信者との関係性\n"
                "- 他の視聴者との関わり\n"
                "- このユーザーの配信に対する貢献度\n"
                "- 特徴的な発言や行動パターン"
            )

        # 送信メッセージの処理
        messages_text = self.messages_text.get("1.0", tk.END).strip()
        send_messages = [msg.strip() for msg in messages_text.split("\n") if msg.strip()]
        if not send_messages:
            send_messages = [f">>{'{no}'} こんにちは、{display_name}さん"]

        # キーワードの処理
        keywords_text = self.keywords_var.get().strip()
        keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
        if not keywords:
            keywords = ["こんにちは", "初見"]

        # 配信者ID別設定の処理
        try:
            import json
            overrides_text = self.overrides_text.get("1.0", tk.END).strip()
            owner_id_overrides = json.loads(overrides_text) if overrides_text else {}
        except json.JSONDecodeError:
            messagebox.showerror("エラー", "配信者ID別設定のJSON形式が正しくありません")
            return

        self.result = {
            "user_id": user_id,
            "display_name": display_name,
            "analysis_enabled": self.analysis_enabled_var.get(),
            "analysis_ai_model": self.ai_model_var.get(),
            "analysis_prompt": prompt_value,
            "template": "user_detail.html",
            "description": self.description_text.get("1.0", tk.END).strip(),
            "tags": [],
            # コメントシステム設定
            "comment_system_enabled": self.comment_enabled_var.get(),
            "send_messages": send_messages,
            "trigger_enabled": self.trigger_enabled_var.get(),
            "trigger_type": self.trigger_type_var.get(),
            "keywords": keywords,
            "max_reactions_per_stream": int(self.max_reactions_var.get() or 1),
            "cooldown_minutes": int(self.cooldown_var.get() or 30),
            "owner_id_overrides": owner_id_overrides
        }
        self.dialog.destroy()

    def cancel_clicked(self):
        self.dialog.destroy()


def main():
    os.makedirs("SpecialUser", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    root = tk.Tk()
    app = NCVSpecialMonitorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
