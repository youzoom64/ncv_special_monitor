"""
ユーザー編集ダイアログ
"""
import tkinter as tk
from tkinter import ttk
import requests
from bs4 import BeautifulSoup

from .utils import log_to_gui
from .broadcaster_dialog import BroadcasterManagementDialog
from .special_trigger_dialog import SpecialTriggerManagementDialog
from .simple_dialogs import SimpleBroadcasterEditDialog


class UserEditDialog:
    def __init__(self, parent, config_manager, user_id=None):
        print(f"[DEBUG] UserEditDialog.__init__() 開始: user_id={user_id}")
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.user_config = config_manager.get_user_config(user_id) if user_id else config_manager.create_default_user_config("")
        print(f"[DEBUG] ユーザー設定読み込み完了: keys={list(self.user_config.keys())}")

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("スペシャルユーザー編集" if user_id else "スペシャルユーザー追加")
        self.dialog.geometry("1000x800")  # 高さを長くする
        self.dialog.transient(parent)
        self.dialog.grab_set()

        print("[DEBUG] UserEditDialog ダイアログセットアップ開始")
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

        # === 左側：編集フォーム ===
        # 基本情報
        basic_frame = ttk.LabelFrame(left_frame, text="基本情報", padding="5")
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

        self.user_enabled_var = tk.BooleanVar(value=self.user_config.get("enabled", True))
        ttk.Checkbutton(basic_frame, text="有効", variable=self.user_enabled_var).grid(row=2, column=1, sticky=tk.W, pady=2)

        basic_frame.columnconfigure(1, weight=1)

        # AI分析設定
        ai_frame = ttk.LabelFrame(left_frame, text="AI分析設定", padding="5")
        ai_frame.pack(fill=tk.X, pady=(0, 10))

        self.analysis_enabled_var = tk.BooleanVar(value=self.user_config.get("ai_analysis", {}).get("enabled", True))
        ttk.Checkbutton(ai_frame, text="AI分析を有効化", variable=self.analysis_enabled_var).pack(anchor=tk.W)

        ttk.Label(ai_frame, text="AIモデル:").pack(anchor=tk.W)
        self.analysis_model_var = tk.StringVar(value=self.user_config.get("ai_analysis", {}).get("model", "openai-gpt4o"))
        ttk.Combobox(ai_frame, textvariable=self.analysis_model_var, values=["openai-gpt4o", "google-gemini-2.5-flash"]).pack(fill=tk.X, pady=2)

        # ★★★ プロンプト設定を追加 ★★★
        ttk.Label(ai_frame, text="プロンプト設定:").pack(anchor=tk.W, pady=(10,0))
        
        self.use_default_prompt_var = tk.BooleanVar(value=self.user_config.get("ai_analysis", {}).get("use_default_prompt", True))
        default_prompt_cb = ttk.Checkbutton(ai_frame, text="デフォルトプロンプトを使用", variable=self.use_default_prompt_var, command=self.on_prompt_mode_change)
        default_prompt_cb.pack(anchor=tk.W)

        # カスタムプロンプト入力エリア
        custom_prompt_frame = ttk.Frame(ai_frame)
        custom_prompt_frame.pack(fill=tk.X, pady=(5,0))
        
        ttk.Label(custom_prompt_frame, text="カスタムプロンプト:").pack(anchor=tk.W)
        
        # テキストエリアとスクロールバー
        prompt_text_frame = ttk.Frame(custom_prompt_frame)
        prompt_text_frame.pack(fill=tk.X, pady=2)
        
        self.custom_prompt_text = tk.Text(prompt_text_frame, height=4, wrap=tk.WORD)
        prompt_scrollbar = ttk.Scrollbar(prompt_text_frame, orient="vertical", command=self.custom_prompt_text.yview)
        self.custom_prompt_text.configure(yscrollcommand=prompt_scrollbar.set)
        
        self.custom_prompt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        prompt_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # カスタムプロンプト内容を設定
        custom_prompt = self.user_config.get("ai_analysis", {}).get("custom_prompt", "")
        if custom_prompt:
            self.custom_prompt_text.insert("1.0", custom_prompt)
        
        # 変数説明ラベル
        variables_help = ttk.Label(custom_prompt_frame, 
            text="使用可能な変数: {user} (ユーザー名), {lv_title} (配信タイトル)", 
            font=("TkDefaultFont", 8))
        variables_help.pack(anchor=tk.W, pady=(2,0))
        
        # プロンプトテンプレートボタン
        template_frame = ttk.Frame(custom_prompt_frame)
        template_frame.pack(fill=tk.X, pady=(5,0))
        
        ttk.Button(template_frame, text="基本テンプレート", command=self.insert_basic_template).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(template_frame, text="詳細分析テンプレート", command=self.insert_detailed_template).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(template_frame, text="リセット", command=self.clear_custom_prompt).pack(side=tk.LEFT)
        
        # 初期状態でプロンプトエリアの有効/無効を設定
        self.on_prompt_mode_change()

        # デフォルト応答設定
        response_frame = ttk.LabelFrame(left_frame, text="デフォルト応答設定", padding="5")
        response_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # デフォルト応答有効チェックボックス
        self.default_response_enabled_var = tk.BooleanVar(value=self.user_config.get("default_response", {}).get("enabled", True))
        ttk.Checkbutton(response_frame, text="デフォルト応答を有効化", variable=self.default_response_enabled_var).pack(anchor=tk.W, pady=(0, 5))

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
        ttk.Entry(reaction_frame, textvariable=self.delay_var, width=10).grid(row=0, column=3, padx=(5, 10))

        ttk.Label(reaction_frame, text="分割送信間隔(秒):").grid(row=0, column=4, sticky=tk.W)
        self.split_delay_var = tk.StringVar(value=str(self.user_config.get("default_response", {}).get("response_split_delay_seconds", 1)))
        ttk.Entry(reaction_frame, textvariable=self.split_delay_var, width=10).grid(row=0, column=5, padx=(5, 0))

        # スペシャルトリガー管理
        triggers_frame = ttk.LabelFrame(left_frame, text="スペシャルトリガー", padding="5")
        triggers_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(triggers_frame, text="スペシャルトリガー管理", command=self.manage_special_triggers).pack()

        # ボタン
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_user).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT)

        # === 右側：配信者一覧 ===
        broadcasters_frame = ttk.LabelFrame(right_frame, text="配信者一覧", padding="5")
        broadcasters_frame.pack(fill=tk.BOTH, expand=True)

        # 配信者一覧Treeview
        self.broadcasters_tree = ttk.Treeview(
            broadcasters_frame,
            columns=("broadcaster_id", "broadcaster_name", "enabled"),
            show="tree headings",
            height=20
        )
        self.broadcasters_tree.heading("#0", text="有効")
        self.broadcasters_tree.heading("broadcaster_id", text="配信者ID")
        self.broadcasters_tree.heading("broadcaster_name", text="配信者名")
        self.broadcasters_tree.heading("enabled", text="状態")

        self.broadcasters_tree.column("#0", width=60)
        self.broadcasters_tree.column("broadcaster_id", width=100)
        self.broadcasters_tree.column("broadcaster_name", width=150)
        self.broadcasters_tree.column("enabled", width=50)

        self.broadcasters_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # ダブルクリックで配信者管理画面へ
        self.broadcasters_tree.bind("<Double-1>", self.on_broadcaster_double_click)
        # チェックボックスクリックイベント
        self.broadcasters_tree.bind("<Button-1>", self.on_broadcaster_click)

        # 配信者操作ボタン
        broadcaster_button_frame = ttk.Frame(broadcasters_frame)
        broadcaster_button_frame.pack(fill=tk.X)

        ttk.Button(broadcaster_button_frame, text="配信者追加", command=self.add_broadcaster).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(broadcaster_button_frame, text="削除", command=self.delete_broadcaster).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(broadcaster_button_frame, text="一括有効", command=self.enable_all_broadcasters).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(broadcaster_button_frame, text="一括無効", command=self.disable_all_broadcasters).pack(side=tk.LEFT, padx=(2, 0))

        # 配信者一覧を初期読み込み
        self.refresh_broadcasters_list()

    def refresh_broadcasters_list(self):
        """配信者一覧を更新"""
        # 既存の項目をクリア
        for item in self.broadcasters_tree.get_children():
            self.broadcasters_tree.delete(item)

        # ユーザー設定から配信者一覧を取得
        if self.user_id:
            user_config = self.config_manager.get_user_config(self.user_id)
            broadcasters = user_config.get("broadcasters", {})

            for broadcaster_id, broadcaster_info in broadcasters.items():
                broadcaster_name = broadcaster_info.get("broadcaster_name", f"配信者{broadcaster_id}")
                enabled = broadcaster_info.get("enabled", True)
                status = "有効" if enabled else "無効"
                checkbox = "☑" if enabled else "☐"

                self.broadcasters_tree.insert(
                    "",
                    tk.END,
                    text=checkbox,
                    values=(broadcaster_id, broadcaster_name, status)
                )

    def on_broadcaster_double_click(self, event):
        """配信者ダブルクリック処理"""
        from .broadcaster_edit_dialog import BroadcasterEditDialog
        
        selection = self.broadcasters_tree.selection()
        if not selection:
            return

        # 選択された配信者の情報を取得
        item_values = self.broadcasters_tree.item(selection[0], "values")
        broadcaster_id = item_values[0]

        # 現在のユーザーIDを取得
        current_user_id = self.user_id or self.user_id_var.get().strip()
        if not current_user_id:
            log_to_gui("ユーザーIDが設定されていません")
            return

        # 配信者編集ダイアログを直接開く
        dialog = BroadcasterEditDialog(self.dialog, self.config_manager, current_user_id, broadcaster_id)
        self.dialog.wait_window(dialog.dialog)

        # ダイアログが閉じられた後、配信者一覧を更新
        self.refresh_broadcasters_list()

    def fetch_user_name(self):
        """ユーザー名取得"""
        user_id = self.user_id_var.get().strip()
        if not user_id:
            log_to_gui("ユーザーIDを入力してください")
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
                log_to_gui(f"ユーザー名を取得しました: {nickname}")
            else:
                self.display_name_var.set(f"ユーザー{user_id}")
                log_to_gui("ユーザー名を取得できませんでした")

        except Exception as e:
            self.display_name_var.set(f"ユーザー{user_id}")
            log_to_gui(f"ユーザー情報の取得に失敗しました: {str(e)}")

    def manage_special_triggers(self):
        """スペシャルトリガー管理"""
        user_id = self.user_id_var.get().strip()
        if not user_id:
            log_to_gui("ユーザーIDを入力してください")
            return

        dialog = SpecialTriggerManagementDialog(self.dialog, self.config_manager, user_id)
        self.dialog.wait_window(dialog.dialog)

    def save_user(self):
        """ユーザー保存"""
        user_id = self.user_id_var.get().strip()
        display_name = self.display_name_var.get().strip()

        if not user_id:
            log_to_gui("ユーザーIDを入力してください")
            return
        if not display_name:
            display_name = f"ユーザー{user_id}"

        # メッセージを処理
        messages_text = self.messages_text.get("1.0", tk.END).strip()
        messages = [msg.strip() for msg in messages_text.split("\n") if msg.strip()]
        if not messages:
            messages = [f">>{'{no}'} こんにちは、{display_name}さん"]

        # ★★★ カスタムプロンプトを取得 ★★★
        custom_prompt = self.custom_prompt_text.get("1.0", tk.END).strip()

        def update_user(config):
            config["user_info"] = {
                "user_id": user_id,
                "display_name": display_name,
                "enabled": self.user_enabled_var.get(),
                "description": "",
                "tags": []
            }
            config["ai_analysis"] = {
                "enabled": self.analysis_enabled_var.get(),
                "model": self.analysis_model_var.get(),
                "use_default_prompt": self.use_default_prompt_var.get(),  # ★ 追加
                "custom_prompt": custom_prompt                            # ★ 追加
            }
            config["default_response"] = {
                "enabled": self.default_response_enabled_var.get(),
                "response_type": self.response_type_var.get(),
                "messages": messages,
                "ai_response_prompt": self.ai_prompt_var.get(),
                "max_reactions_per_stream": int(self.max_reactions_var.get() or 1),
                "response_delay_seconds": int(self.delay_var.get() or 0),
                "response_split_delay_seconds": float(self.split_delay_var.get() or 1)
            }
            # 既存を維持
            config["special_triggers"] = config.get("special_triggers", [])
            config["broadcasters"] = config.get("broadcasters", {})

        if self.config_manager._safe_save_user_config(user_id, update_user):
            self.result = True
            self.dialog.destroy()
            log_to_gui(f"ユーザー '{display_name}' の設定を保存しました")
        else:
            log_to_gui("ユーザー設定の保存に失敗しました")


    def cancel(self):
        self.dialog.destroy()

    def add_broadcaster(self):
        """配信者追加"""
        current_user_id = self.user_id or self.user_id_var.get().strip()
        if not current_user_id:
            log_to_gui("ユーザーIDが設定されていません")
            return

        # 簡単な配信者追加ダイアログ
        dialog = SimpleBroadcasterEditDialog(self.dialog, self.config_manager, current_user_id)
        self.dialog.wait_window(dialog.dialog)

        if dialog.result:
            self.refresh_broadcasters_list()

    def delete_broadcaster(self):
        """配信者削除"""
        selection = self.broadcasters_tree.selection()
        if not selection:
            log_to_gui("削除する配信者を選択してください")
            return

        current_user_id = self.user_id or self.user_id_var.get().strip()
        if not current_user_id:
            log_to_gui("ユーザーIDが設定されていません")
            return

        # 選択された配信者の情報を取得
        item_values = self.broadcasters_tree.item(selection[0], "values")
        broadcaster_id = item_values[0]
        broadcaster_name = item_values[1]

        # 確認ダイアログ
        import tkinter.messagebox as msgbox
        if msgbox.askyesno("確認", f"配信者 '{broadcaster_name}' を削除しますか？"):
            user_config = self.config_manager.get_user_config(current_user_id)
            broadcasters = user_config.get("broadcasters", {})
            if broadcaster_id in broadcasters:
                del broadcasters[broadcaster_id]
                user_config["broadcasters"] = broadcasters
                self.config_manager.save_user_config(current_user_id, user_config)
                self.refresh_broadcasters_list()
                log_to_gui(f"配信者 '{broadcaster_name}' を削除しました")

    def on_broadcaster_click(self, event):
        """配信者のチェックボックスクリック処理"""
        item = self.broadcasters_tree.identify('item', event.x, event.y)
        column = self.broadcasters_tree.identify('column', event.x, event.y)

        # チェックボックス列（#0）がクリックされた場合
        if item and column == "#0":
            current_user_id = self.user_id or self.user_id_var.get().strip()
            if not current_user_id:
                log_to_gui("ユーザーIDが設定されていません")
                return

            # 選択された配信者の情報を取得
            item_values = self.broadcasters_tree.item(item, "values")
            broadcaster_id = item_values[0]
            broadcaster_name = item_values[1]

            # 現在の状態を取得し、切り替える
            user_config = self.config_manager.get_user_config(current_user_id)
            broadcasters = user_config.get("broadcasters", {})
            if broadcaster_id in broadcasters:
                current_enabled = broadcasters[broadcaster_id].get("enabled", True)
                new_enabled = not current_enabled

                # 汎用保存ロジックを使用
                def update_broadcaster_enabled(config):
                    broadcasters = config.get("broadcasters", {})
                    if broadcaster_id in broadcasters:
                        broadcasters[broadcaster_id]["enabled"] = new_enabled
                        config["broadcasters"] = broadcasters

                if self.config_manager._safe_save_user_config(current_user_id, update_broadcaster_enabled):
                    self.refresh_broadcasters_list()
                    action = "有効" if new_enabled else "無効"
                    log_to_gui(f"配信者 '{broadcaster_name}' を{action}にしました")
                else:
                    log_to_gui("配信者の設定更新に失敗しました")

    def enable_all_broadcasters(self):
        """すべての配信者を有効化"""
        self._toggle_all_broadcasters_enabled(True)

    def disable_all_broadcasters(self):
        """すべての配信者を無効化"""
        self._toggle_all_broadcasters_enabled(False)

    def _toggle_all_broadcasters_enabled(self, enabled):
        """すべての配信者の有効/無効を切り替え"""
        current_user_id = self.user_id or self.user_id_var.get().strip()
        if not current_user_id:
            log_to_gui("ユーザーIDが設定されていません")
            return

        # 汎用保存ロジックを使用
        def update_all_broadcasters_enabled(config):
            broadcasters = config.get("broadcasters", {})
            if not broadcasters:
                return False
            # すべての配信者の設定を更新
            for broadcaster_id, broadcaster_info in broadcasters.items():
                broadcaster_info["enabled"] = enabled
            config["broadcasters"] = broadcasters
            return True

        if self.config_manager._safe_save_user_config(current_user_id, update_all_broadcasters_enabled):
            self.refresh_broadcasters_list()
            action = "有効" if enabled else "無効"
            log_to_gui(f"すべての配信者を{action}にしました")
        else:
            log_to_gui("配信者設定の更新に失敗しました")


    def on_prompt_mode_change(self):
        """プロンプトモード変更時の処理"""
        use_default = self.use_default_prompt_var.get()
        
        # カスタムプロンプトエリアの有効/無効を切り替え
        state = tk.DISABLED if use_default else tk.NORMAL
        self.custom_prompt_text.config(state=state)
        
        if use_default:
            # デフォルトプロンプトを使用する場合は背景色を変更
            self.custom_prompt_text.config(bg="#f0f0f0")
        else:
            # カスタムプロンプトを使用する場合は通常の背景色
            self.custom_prompt_text.config(bg="white")

    def insert_basic_template(self):
        """基本テンプレートを挿入"""
        template = """「{user}」さんの「{lv_title}」でのコメント行動を分析してください。

    以下の観点から詳しく分析をお願いします：
    - コメントの頻度と投稿パターン
    - 配信への参加度や貢献度
    - コメント内容の特徴や傾向
    - 他の視聴者との交流の様子

    分析結果はHTML形式で出力し、読みやすく整理してください。"""
        
        self.custom_prompt_text.delete("1.0", tk.END)
        self.custom_prompt_text.insert("1.0", template)

    def insert_detailed_template(self):
        """詳細分析テンプレートを挿入"""
        template = """配信視聴者「{user}」の行動分析レポート
    対象配信：「{lv_title}」

    【分析項目】
    1. 基本統計
    - 総コメント数と投稿時間分布
    - 平均コメント長と文字数傾向

    2. 参加パターン分析
    - 配信参加のタイミング（開始直後、中盤、終盤など）
    - コメント投稿の時間間隔と集中度

    3. コミュニケーション分析
    - 配信者への直接的な反応やコメント
    - 他視聴者との交流の有無と内容

    4. 内容分析
    - 感情表現の傾向（ポジティブ/ネガティブ）
    - 話題への反応パターン
    - 独自性のあるコメントや印象的な発言

    5. 総合評価
    - このユーザーの配信における位置づけ
    - コミュニティへの貢献度
    - 今後の関係性に関する提案

    分析結果はHTML形式で、各項目を<h3>タグで整理し、<br>タグで改行して出力してください。"""
        
        self.custom_prompt_text.delete("1.0", tk.END)
        self.custom_prompt_text.insert("1.0", template)

    def clear_custom_prompt(self):
        """カスタムプロンプトをクリア"""
        self.custom_prompt_text.delete("1.0", tk.END)