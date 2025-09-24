#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
スペシャルトリガー保存テストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_manager import HierarchicalConfigManager
import uuid

def test_special_trigger_save():
    print("=== スペシャルトリガー保存テスト ===")

    config_manager = HierarchicalConfigManager()

    # テスト用ユーザー
    test_user_id = "21639740"
    test_display_name = "アニメ豚太郎"

    print(f"テストユーザー: {test_user_id} ({test_display_name})")

    # 既存設定を取得
    user_config = config_manager.get_user_config(test_user_id)
    existing_triggers = user_config.get('special_triggers', [])
    print(f"既存スペシャルトリガー数: {len(existing_triggers)}")

    # 新しいスペシャルトリガーを作成
    test_trigger_config = {
        "id": str(uuid.uuid4()),
        "name": "テスト緊急トリガー",
        "enabled": True,
        "keywords": ["緊急", "助けて", "SOS"],
        "keyword_condition": "OR",
        "response_type": "ai",
        "ai_response_prompt": "緊急事態に対して適切かつ親身に対応してください",
        "ignore_all_limits": True,
        "firing_probability": 100
    }

    print(f"スペシャルトリガーを追加: {test_trigger_config['name']}")
    config_manager.save_special_trigger_config(test_user_id, test_trigger_config)

    # 保存後の確認
    updated_config = config_manager.get_user_config(test_user_id)
    special_triggers = updated_config.get("special_triggers", [])
    print(f"保存後スペシャルトリガー数: {len(special_triggers)}")

    # 追加したトリガーが保存されているか確認
    found_trigger = None
    for trigger in special_triggers:
        if trigger.get("id") == test_trigger_config["id"]:
            found_trigger = trigger
            break

    if found_trigger:
        print("OK 新しいスペシャルトリガーが保存されました")
        print(f"  ID: {found_trigger.get('id')}")
        print(f"  名前: {found_trigger.get('name')}")
        print(f"  有効: {found_trigger.get('enabled')}")
        print(f"  キーワード: {found_trigger.get('keywords')}")
        print(f"  応答タイプ: {found_trigger.get('response_type')}")
    else:
        print("NG 新しいスペシャルトリガーが保存されていません")

    # ディレクトリのconfig.jsonを直接確認
    print("\n=== ディレクトリ配下のconfig.json確認 ===")
    try:
        dir_config = config_manager.load_user_config_from_directory(test_user_id, test_display_name)
        dir_special_triggers = dir_config.get("special_triggers", [])
        print(f"ディレクトリスペシャルトリガー数: {len(dir_special_triggers)}")

        # 追加したトリガーがディレクトリにも保存されているか確認
        found_in_dir = False
        for trigger in dir_special_triggers:
            if trigger.get("id") == test_trigger_config["id"]:
                found_in_dir = True
                break

        if found_in_dir:
            print("OK ディレクトリのconfig.jsonにも保存されています")
        else:
            print("NG ディレクトリのconfig.jsonに保存されていません")

    except Exception as e:
        print(f"NG ディレクトリ読み込みエラー: {str(e)}")

    print("\n=== 完全な構造確認 ===")
    try:
        dir_config = config_manager.load_user_config_from_directory(test_user_id, test_display_name)

        print("config.jsonの構造:")
        print(f"  user_info: {dir_config.get('user_info', {}).get('display_name', 'N/A')}")
        print(f"  broadcasters: {len(dir_config.get('broadcasters', {}))}人")
        print(f"  special_triggers: {len(dir_config.get('special_triggers', []))}個")

        # スペシャルトリガーの詳細表示
        if dir_config.get('special_triggers'):
            print("  スペシャルトリガー詳細:")
            for i, trigger in enumerate(dir_config.get('special_triggers', []), 1):
                print(f"    {i}. {trigger.get('name', 'N/A')} ({trigger.get('keywords', [])})")

    except Exception as e:
        print(f"NG 構造確認エラー: {str(e)}")

    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_special_trigger_save()