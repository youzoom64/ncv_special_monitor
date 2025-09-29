# bulk_broadcaster_registration.py - 一括配信者登録機能
import os
import json
import logging
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading

# メインアプリからログ出力するための関数をインポート
def log_to_gui(message):
    """ログ出力のためのダミー関数（main.pyから上書きされる）"""
    print(message)

from config_manager import HierarchicalConfigManager
from .specialuser_follow_fetcher import (
    setup_driver, fetch_follow_list, should_skip_user_id,
    load_config as load_old_config, sanitize_for_fs, DEBUGLOG
)

class BulkBroadcasterRegistration:
    def __init__(self, config_manager: HierarchicalConfigManager):
        self.config_manager = config_manager
        self.logger = logging.getLogger("bulk_registration")

    def fetch_follows_for_user(self, user_id: str, progress_callback=None) -> list:
        """指定ユーザーのフォロー一覧を取得"""
        if should_skip_user_id(user_id):
            self.logger.warning(f"Skipped user_id: {user_id}")
            return []

        driver = None
        try:
            if progress_callback:
                progress_callback(f"Seleniumドライバーを起動中...")

            driver = setup_driver()

            if progress_callback:
                progress_callback(f"ユーザー {user_id} のフォロー一覧を取得中...")

            follows = fetch_follow_list(user_id, driver)

            if progress_callback:
                progress_callback(f"取得完了: {len(follows)}人のフォローを発見")

            return follows

        except Exception as e:
            self.logger.error(f"フォロー取得エラー: {str(e)}")
            if progress_callback:
                progress_callback(f"エラー: {str(e)}")
            return []
        finally:
            if driver:
                driver.quit()

    def register_broadcasters_from_follows(self, user_id: str, follows: list, selected_ids: list = None) -> int:
        """フォロー一覧から配信者を一括登録"""
        if selected_ids is None:
            selected_ids = [f["follow_user_id"] for f in follows]

        registered_count = 0

        for follow in follows:
            follow_user_id = follow.get("follow_user_id", "")
            follow_user_name = follow.get("follow_user_name", "")

            if follow_user_id not in selected_ids:
                continue

            if should_skip_user_id(follow_user_id):
                continue

            try:
                # 既存の配信者設定をチェック
                existing_broadcasters = self.config_manager.get_user_broadcasters(user_id)
                if follow_user_id in existing_broadcasters:
                    self.logger.info(f"配信者 {follow_user_id} は既に登録済み")
                    continue

                # 新しい配信者設定を作成
                broadcaster_config = self.config_manager.create_default_broadcaster_config(
                    follow_user_id, follow_user_name
                )

                # 配信者を登録
                self.config_manager.save_broadcaster_config(user_id, follow_user_id, broadcaster_config)
                registered_count += 1
                self.logger.info(f"配信者登録: {follow_user_name} ({follow_user_id})")

            except Exception as e:
                self.logger.error(f"配信者登録エラー {follow_user_id}: {str(e)}")

        return registered_count

    def load_existing_follows_from_file(self, user_id: str, display_name: str) -> list:
        """既存のfollow.jsonファイルから読み込み"""
        specialuser_root = Path("SpecialUser")
        user_dir = specialuser_root / f"{sanitize_for_fs(user_id)}_{sanitize_for_fs(display_name)}"
        follow_path = user_dir / "follow.json"

        if not follow_path.exists():
            return []

        try:
            with open(follow_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"follow.json読み込みエラー: {str(e)}")
            return []


class BulkRegistrationDialog:
    def __init__(self, parent, config_manager: HierarchicalConfigManager, user_id: str, user_display_name: str):
        self.result = False
        self.config_manager = config_manager
        self.user_id = user_id
        self.user_display_name = user_display_name
        self.bulk_registration = BulkBroadcasterRegistration(config_manager)
        self.follows_data = []

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"一括配信者登録 - {user_display_name}")
        self.dialog.geometry("800x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()
        self.load_existing_follows()

    def setup_dialog(self):
        """ダイアログセットアップ"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 説明
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        info_label = ttk.Label(info_frame,
                              text=f"ユーザー「{self.user_display_name}」のフォロー一覧から配信者を一括登録します",
                              font=("", 10))
        info_label.pack(anchor=tk.W)

        # 操作ボタン
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(action_frame, text="最新のフォロー一覧を取得",
                  command=self.fetch_fresh_follows).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="既存ファイルから読み込み",
                  command=self.load_existing_follows).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(action_frame, text="JSONファイルから読み込み",
                  command=self.load_from_file).pack(side=tk.LEFT, padx=(5, 0))

        # プログレスバー
        self.progress_var = tk.StringVar(value="")
        self.progress_label = ttk.Label(main_frame, textvariable=self.progress_var)
        self.progress_label.pack(anchor=tk.W, pady=(0, 5))

        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # フォロー一覧
        list_frame = ttk.LabelFrame(main_frame, text="フォロー一覧", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 選択操作
        select_frame = ttk.Frame(list_frame)
        select_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(select_frame, text="全選択", command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(select_frame, text="全解除", command=self.select_none).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(select_frame, text="既存配信者を除外", command=self.exclude_existing).pack(side=tk.LEFT, padx=(5, 0))

        # フォロー一覧表示
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.follows_tree = ttk.Treeview(
            tree_frame,
            columns=("user_id", "user_name", "status"),
            show="tree headings",
            height=15
        )
        self.follows_tree.heading("#0", text="選択")
        self.follows_tree.heading("user_id", text="ユーザーID")
        self.follows_tree.heading("user_name", text="ユーザー名")
        self.follows_tree.heading("status", text="状態")

        self.follows_tree.column("#0", width=60)
        self.follows_tree.column("user_id", width=100)
        self.follows_tree.column("user_name", width=200)
        self.follows_tree.column("status", width=100)

        self.follows_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # スクロールバー
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.follows_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.follows_tree.configure(yscrollcommand=scrollbar.set)

        # 統計情報
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.stats_var = tk.StringVar(value="フォロー一覧を読み込んでください")
        ttk.Label(stats_frame, textvariable=self.stats_var).pack(anchor=tk.W)

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="選択した配信者を登録",
                  command=self.register_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="閉じる", command=self.close_dialog).pack(side=tk.RIGHT)

    def update_progress(self, message: str):
        """プログレス更新"""
        self.progress_var.set(message)
        self.dialog.update()

    def fetch_fresh_follows(self):
        """最新のフォロー一覧を取得"""
        def fetch_thread():
            try:
                self.progress_bar.start()
                self.update_progress("フォロー一覧を取得中...")

                follows = self.bulk_registration.fetch_follows_for_user(
                    self.user_id, self.update_progress
                )

                self.follows_data = follows
                self.dialog.after(0, self.refresh_follows_list)
                self.dialog.after(0, lambda: self.update_progress(f"取得完了: {len(follows)}人"))

            except Exception as e:
                self.dialog.after(0, lambda: self.update_progress(f"エラー: {str(e)}"))
            finally:
                self.dialog.after(0, self.progress_bar.stop)

        threading.Thread(target=fetch_thread, daemon=True).start()

    def load_existing_follows(self):
        """既存のfollow.jsonから読み込み"""
        try:
            self.update_progress("既存ファイルから読み込み中...")
            follows = self.bulk_registration.load_existing_follows_from_file(
                self.user_id, self.user_display_name
            )
            self.follows_data = follows
            self.refresh_follows_list()
            self.update_progress(f"読み込み完了: {len(follows)}人")
        except Exception as e:
            self.update_progress(f"読み込みエラー: {str(e)}")

    def load_from_file(self):
        """JSONファイルから読み込み"""
        file_path = filedialog.askopenfilename(
            title="フォロー一覧JSONファイルを選択",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                self.follows_data = data
            else:
                self.follows_data = []

            self.refresh_follows_list()
            self.update_progress(f"ファイル読み込み完了: {len(self.follows_data)}人")

        except Exception as e:
            log_to_gui(f"ファイル読み込みエラー: {str(e)}")

    def refresh_follows_list(self):
        """フォロー一覧を更新"""
        # 既存項目をクリア
        for item in self.follows_tree.get_children():
            self.follows_tree.delete(item)

        # 既存配信者を取得
        existing_broadcasters = self.config_manager.get_user_broadcasters(self.user_id)

        # フォロー一覧を表示
        for follow in self.follows_data:
            user_id = follow.get("follow_user_id", "")
            user_name = follow.get("follow_user_name", "")

            # 状態を判定
            if should_skip_user_id(user_id):
                status = "スキップ"
            elif user_id in existing_broadcasters:
                status = "登録済み"
            else:
                status = "未登録"

            # TreeViewに追加（デフォルトで未登録のみチェック）
            item = self.follows_tree.insert(
                "",
                tk.END,
                text="☐" if status == "未登録" else "",
                values=(user_id, user_name, status)
            )

        self.update_stats()

    def update_stats(self):
        """統計情報を更新"""
        total = len(self.follows_data)
        existing_broadcasters = self.config_manager.get_user_broadcasters(self.user_id)
        already_registered = sum(1 for f in self.follows_data
                               if f.get("follow_user_id") in existing_broadcasters)
        skipped = sum(1 for f in self.follows_data
                     if should_skip_user_id(f.get("follow_user_id", "")))
        available = total - already_registered - skipped

        self.stats_var.set(f"総数: {total}人 | 登録済み: {already_registered}人 | "
                          f"登録可能: {available}人 | スキップ: {skipped}人")

    def select_all(self):
        """全選択"""
        for item in self.follows_tree.get_children():
            values = self.follows_tree.item(item, "values")
            if values[2] == "未登録":  # 未登録のみ選択
                self.follows_tree.item(item, text="☑")

    def select_none(self):
        """全解除"""
        for item in self.follows_tree.get_children():
            self.follows_tree.item(item, text="☐")

    def exclude_existing(self):
        """既存配信者を除外"""
        for item in self.follows_tree.get_children():
            values = self.follows_tree.item(item, "values")
            if values[2] in ["登録済み", "スキップ"]:
                self.follows_tree.item(item, text="")
            else:
                self.follows_tree.item(item, text="☑")

    def get_selected_follows(self) -> list:
        """選択されたフォローを取得"""
        selected = []
        for item in self.follows_tree.get_children():
            text = self.follows_tree.item(item, "text")
            if text == "☑":
                values = self.follows_tree.item(item, "values")
                user_id = values[0]
                # 対応するフォローデータを検索
                for follow in self.follows_data:
                    if follow.get("follow_user_id") == user_id:
                        selected.append(follow)
                        break
        return selected

    def register_selected(self):
        """選択された配信者を登録"""
        selected_follows = self.get_selected_follows()

        if not selected_follows:
            log_to_gui("登録する配信者を選択してください")
            return

        # 確認なしで登録

        try:
            self.update_progress("配信者を登録中...")

            selected_ids = [f.get("follow_user_id") for f in selected_follows]
            registered_count = self.bulk_registration.register_broadcasters_from_follows(
                self.user_id, self.follows_data, selected_ids
            )

            self.update_progress(f"登録完了: {registered_count}人")
            log_to_gui(f"{registered_count}人の配信者を登録しました")

            # 一覧を更新
            self.refresh_follows_list()

        except Exception as e:
            log_to_gui(f"登録エラー: {str(e)}")

    def close_dialog(self):
        self.result = True
        self.dialog.destroy()


def show_bulk_registration_dialog(parent, config_manager: HierarchicalConfigManager,
                                 user_id: str, user_display_name: str):
    """一括登録ダイアログを表示"""
    dialog = BulkRegistrationDialog(parent, config_manager, user_id, user_display_name)
    parent.wait_window(dialog.dialog)
    return dialog.result