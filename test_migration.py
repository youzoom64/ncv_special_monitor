#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
設定移行テストスクリプト
既存のグローバル設定からスペシャルユーザーディレクトリ配下への移行をテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_manager import HierarchicalConfigManager

def main():
    print("=== 設定移行テスト ===")

    config_manager = HierarchicalConfigManager()

    # 既存のユーザー一覧を取得
    print("\n1. 既存ユーザーの確認:")
    all_users = config_manager.get_all_special_users()
    print(f"既存ユーザー数: {len(all_users)}")

    for user_id, user_info in all_users.items():
        display_name = user_info.get("display_name", f"ユーザー{user_id}")
        print(f"  - {user_id}: {display_name}")

    # 各ユーザーを移行
    print("\n2. ユーザー移行:")
    for user_id in all_users.keys():
        print(f"  移行中: {user_id}")
        try:
            new_config = config_manager.migrate_user_from_global_config(user_id)
            print(f"  OK 移行完了: {user_id}")

            # 移行後の設定を確認
            display_name = new_config["user_info"]["display_name"]
            broadcasters_count = len(new_config.get("broadcasters", {}))
            special_triggers_count = len(new_config.get("special_triggers", []))

            print(f"    - 配信者数: {broadcasters_count}")
            print(f"    - スペシャルトリガー数: {special_triggers_count}")

        except Exception as e:
            print(f"  NG 移行エラー: {user_id} - {str(e)}")

    # 移行後のディレクトリ構造を確認
    print("\n3. 移行後のディレクトリ構造:")
    user_dirs = config_manager.get_all_user_directories()
    print(f"スペシャルユーザーディレクトリ数: {len(user_dirs)}")

    for user_dir in user_dirs:
        user_id = user_dir["user_id"]
        display_name = user_dir["display_name"]
        path = user_dir["path"]

        print(f"  - {user_id}_{display_name}")
        config_path = path / "config.json"
        if config_path.exists():
            print(f"    OK config.json存在")

            # 設定内容を確認
            try:
                config = config_manager.load_user_config_from_directory(user_id, display_name)
                broadcasters_count = len(config.get("broadcasters", {}))
                special_triggers_count = len(config.get("special_triggers", []))
                print(f"    - 配信者: {broadcasters_count}人")
                print(f"    - スペシャルトリガー: {special_triggers_count}個")
            except Exception as e:
                print(f"    NG 設定読み込みエラー: {str(e)}")
        else:
            print(f"    NG config.jsonなし")

    print("\n=== 移行テスト完了 ===")

if __name__ == "__main__":
    main()