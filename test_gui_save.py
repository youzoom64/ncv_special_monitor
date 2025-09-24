#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI保存テストスクリプト
新しい設定保存方式をテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_manager import HierarchicalConfigManager

def test_broadcaster_save():
    print("=== 配信者保存テスト ===")

    config_manager = HierarchicalConfigManager()

    # テスト用ユーザー
    test_user_id = "21639740"
    test_display_name = "アニメ豚太郎"

    print(f"テストユーザー: {test_user_id} ({test_display_name})")

    # 既存設定を取得
    user_config = config_manager.get_user_config(test_user_id)
    print(f"既存配信者数: {len(user_config.get('broadcasters', {}))}")

    # 新しい配信者を追加
    test_broadcaster_id = "TEST_BROADCASTER_123"
    test_broadcaster_name = "テスト配信者"

    broadcaster_config = {
        "broadcaster_id": test_broadcaster_id,
        "broadcaster_name": test_broadcaster_name,
        "enabled": True,
        "default_response": {
            "response_type": "predefined",
            "messages": [f">>{'{no}'} {test_broadcaster_name}での挨拶です"],
            "ai_response_prompt": f"{test_broadcaster_name}の配信に特化した親しみやすい返答をしてください",
            "max_reactions_per_stream": 1,
            "response_delay_seconds": 0
        },
        "triggers": []
    }

    print(f"配信者を追加: {test_broadcaster_id} ({test_broadcaster_name})")
    config_manager.save_broadcaster_config(test_user_id, test_broadcaster_id, broadcaster_config)

    # 保存後の確認
    updated_config = config_manager.get_user_config(test_user_id)
    broadcasters = updated_config.get("broadcasters", {})
    print(f"保存後配信者数: {len(broadcasters)}")

    if test_broadcaster_id in broadcasters:
        print("OK 新しい配信者が保存されました")
        saved_broadcaster = broadcasters[test_broadcaster_id]
        print(f"  ID: {saved_broadcaster.get('broadcaster_id')}")
        print(f"  名前: {saved_broadcaster.get('broadcaster_name')}")
        print(f"  有効: {saved_broadcaster.get('enabled')}")
    else:
        print("NG 新しい配信者が保存されていません")

    # ディレクトリのconfig.jsonを直接確認
    print("\n=== ディレクトリ配下のconfig.json確認 ===")
    try:
        dir_config = config_manager.load_user_config_from_directory(test_user_id, test_display_name)
        dir_broadcasters = dir_config.get("broadcasters", {})
        print(f"ディレクトリ配信者数: {len(dir_broadcasters)}")

        if test_broadcaster_id in dir_broadcasters:
            print("OK ディレクトリのconfig.jsonにも保存されています")
        else:
            print("NG ディレクトリのconfig.jsonに保存されていません")

    except Exception as e:
        print(f"NG ディレクトリ読み込みエラー: {str(e)}")

    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_broadcaster_save()