import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import requests
from bs4 import BeautifulSoup
import json
import time

from config_manager import NCVSpecialConfigManager
from logger import NCVSpecialLogger
from file_monitor import NCVFolderMonitor
from broadcast_detector import BroadcastEndDetector
from pipeline import PipelineExecutor


class NCVSpecialMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NCV Special User Monitor")
        self.root.geometry("800x600")
        
        # コンポーネント初期化
        self.config_manager = NCVSpecialConfigManager()
        self.logger = NCVSpecialLogger()
        self.pipeline_executor = PipelineExecutor(self.config_manager, self.logger)
        self.broadcast_detector = BroadcastEndDetector(self.config_manager, self.logger, self.pipeline_executor)
        self.file_monitor = NCVFolderMonitor(self.config_manager, self.logger, self.broadcast_detector)
        
        # パイプラインエグゼキューターにファイルモニターを設定
        self.pipeline_executor.file_monitor = self.file_monitor
        
        self.setup_gui()
        self.load_config()
        
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
        
        self.users_tree = ttk.Treeview(users_frame, columns=("user_id", "display_name", "ai_model", "custom_prompt"), show="headings", height=8)
        self.users_tree.heading("user_id", text="ユーザーID")
        self.users_tree.heading("display_name", text="表示名")
        self.users_tree.heading("ai_model", text="AIモデル")
        self.users_tree.heading("custom_prompt", text="カスタムプロンプト")
        self.users_tree.column("user_id", width=100)
        self.users_tree.column("display_name", width=150)
        self.users_tree.column("ai_model", width=120)
        self.users_tree.column("custom_prompt", width=100)
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
            self.users_tree.insert("", tk.END, values=(
                user_data["user_id"],
                user_data["display_name"],
                user_data["analysis_ai_model"],
                "設定済み" if user_data["analysis_prompt"] else "デフォルト"
            ))

    def edit_special_user(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "編集するユーザーを選択してください")
            return
        values = self.users_tree.item(selected[0], "values")
        user_id = values[0]
        config = self.config_manager.load_config()
        users = config.get("special_users_config", {}).get("users", {})
        user_config = users.get(user_id, {})
        dialog = UserEditDialog(self.root, user_config)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            user_data = dialog.result
            self.users_tree.item(selected[0], values=(
                user_data["user_id"],
                user_data["display_name"],
                user_data["analysis_ai_model"],
                "設定済み" if user_data["analysis_prompt"] else "デフォルト"
            ))

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
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        for user_id, user_config in users.items():
            display_name = user_config.get("display_name", f"ユーザー{user_id}")
            ai_model = user_config.get("analysis_ai_model", "openai-gpt4o")
            has_custom_prompt = bool(user_config.get("analysis_prompt", ""))
            self.users_tree.insert("", tk.END, values=(
                user_id,
                display_name,
                ai_model,
                "設定済み" if has_custom_prompt else "デフォルト"
            ))
    
    def save_config(self):
        try:
            config = self.config_manager.load_config()
            config["ncv_folder_path"] = self.ncv_path_var.get()
            config["monitor_enabled"] = self.monitor_enabled_var.get()
            config["check_interval_minutes"] = int(self.check_interval_var.get())
            config["api_settings"]["summary_ai_model"] = self.ai_model_var.get()
            config["api_settings"]["openai_api_key"] = self.openai_key_var.get()
            config["api_settings"]["google_api_key"] = self.google_key_var.get()
            existing_users = config.get("special_users_config", {}).get("users", {})
            current_tree_users = {}
            for item in self.users_tree.get_children():
                values = self.users_tree.item(item, "values")
                user_id = values[0]
                if user_id in existing_users:
                    current_tree_users[user_id] = existing_users[user_id]
                else:
                    current_tree_users[user_id] = {
                        "user_id": user_id,
                        "display_name": values[1],
                        "analysis_enabled": True,
                        "analysis_ai_model": values[2],
                        "analysis_prompt": "",
                        "template": "user_detail.html",
                        "description": "",
                        "tags": []
                    }
            config["special_users_config"]["users"] = current_tree_users
            self.config_manager.save_config(config)
            messagebox.showinfo("成功", "設定を保存しました")
        except Exception as e:
            messagebox.showerror("エラー", f"設定保存エラー: {str(e)}")
    
    def start_monitoring(self):
        try:
            self.save_config()
            self.file_monitor.start_monitoring()
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
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(main_frame, text="ユーザーID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.user_id_var = tk.StringVar(value=self.user_config.get("user_id", ""))
        user_id_frame = ttk.Frame(main_frame)
        user_id_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.user_id_entry = ttk.Entry(user_id_frame, textvariable=self.user_id_var, width=20)
        self.user_id_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.fetch_button = ttk.Button(user_id_frame, text="名前取得", command=self.fetch_user_name)
        self.fetch_button.grid(row=0, column=1, padx=(5, 0))
        
        ttk.Label(main_frame, text="表示名:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.display_name_var = tk.StringVar(value=self.user_config.get("display_name", ""))
        ttk.Entry(main_frame, textvariable=self.display_name_var, width=35).grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(main_frame, text="AIモデル:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.ai_model_var = tk.StringVar(value=self.user_config.get("analysis_ai_model", "openai-gpt4o"))
        ai_model_combo = ttk.Combobox(main_frame, textvariable=self.ai_model_var, values=["openai-gpt4o", "google-gemini-2.5-flash"])
        ai_model_combo.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.analysis_enabled_var = tk.BooleanVar(value=self.user_config.get("analysis_enabled", True))
        ttk.Checkbutton(main_frame, text="AI分析を有効化", variable=self.analysis_enabled_var).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(main_frame, text="カスタムプロンプト:").grid(row=4, column=0, padx=5, pady=5, sticky=(tk.W, tk.N))
        prompt_frame = ttk.Frame(main_frame)
        prompt_frame.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.prompt_text = tk.Text(prompt_frame, height=10, width=50)
        self.prompt_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        prompt_scrollbar = ttk.Scrollbar(prompt_frame, orient=tk.VERTICAL, command=self.prompt_text.yview)
        prompt_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.prompt_text.configure(yscrollcommand=prompt_scrollbar.set)
        default_prompt = """以下のユーザーのコメント履歴を分析して、このユーザーの特徴、傾向、配信との関わり方について詳しく分析してください。

分析観点：
- コメントの頻度と投稿タイミング
- コメント内容の傾向（質問、感想、ツッコミなど）
- 配信者との関係性
- 他の視聴者との関わり
- このユーザーの配信に対する貢献度
- 特徴的な発言や行動パターン"""
        current_prompt = self.user_config.get("analysis_prompt", default_prompt)
        self.prompt_text.insert("1.0", current_prompt)
        
        ttk.Label(main_frame, text="説明・メモ:").grid(row=5, column=0, padx=5, pady=5, sticky=(tk.W, tk.N))
        self.description_text = tk.Text(main_frame, height=3, width=50)
        self.description_text.grid(row=5, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.description_text.insert("1.0", self.user_config.get("description", ""))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=20)
        ttk.Button(button_frame, text="保存", command=self.ok_clicked).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.cancel_clicked).grid(row=0, column=1, padx=5)
        
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        user_id_frame.columnconfigure(0, weight=1)
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)
        if not user_config:
            self.user_id_entry.focus()

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
        self.result = {
            "user_id": user_id,
            "display_name": display_name,
            "analysis_enabled": self.analysis_enabled_var.get(),
            "analysis_ai_model": self.ai_model_var.get(),
            "analysis_prompt": self.prompt_text.get("1.0", tk.END).strip(),
            "template": "user_detail.html",
            "description": self.description_text.get("1.0", tk.END).strip(),
            "tags": []
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
