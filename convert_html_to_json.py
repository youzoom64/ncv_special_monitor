#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTMLファイルからコメントデータを抽出してJSON形式に変換するスクリプト
"""

import os
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

def parse_html_to_json(html_file_path: str, output_dir: str = "converted_data"):
    """HTMLファイルを解析してJSON形式に変換"""
    
    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)
    
    # HTMLファイル読み込み
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # ユーザー名を取得（タイトルから）
    title = soup.find('title')
    user_name = "チンカスアニメ豚太郎"  # HTMLから判断
    user_id = "21639740"  # HTMLから判断
    
    # 各配信セクションを取得
    link_items = soup.find_all('div', class_='link-item')
    
    converted_count = 0
    
    for item in link_items:
        try:
            # 開始時間を取得
            start_time_text = None
            for p in item.find_all('p'):
                if '開始時間:' in p.text:
                    start_time_text = p.text.replace('開始時間:', '').strip()
                    break
            
            if not start_time_text:
                continue
            
            # リンクからlv番号を取得
            link = item.find('a')
            if not link or not link.get('href'):
                continue
            
            href = link.get('href')
            lv_match = re.search(r'(\d+)_21639740_comment\.html', href)
            if not lv_match:
                continue
            
            lv_number = lv_match.group(1)
            lv_value = f"lv{lv_number}"
            
            # 配信タイトルを取得（リンクテキストから）
            link_text = link.text.strip()
            # "〜における〜のコメント分析"の部分から配信タイトルを抽出
            title_match = re.search(r'^([^:]+):', link_text)
            live_title = title_match.group(1) if title_match else "配信"
            
            # コメントテーブルを取得
            chat_data_div = item.find('div', class_='chat-data')
            if not chat_data_div:
                continue
            
            table = chat_data_div.find('table')
            if not table:
                continue
            
            # コメントデータを抽出
            comments = []
            rows = table.find_all('tr')[1:]  # ヘッダー行をスキップ
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    comment_no = int(cells[0].text.strip())
                    elapsed_time = cells[1].text.strip()
                    date_str = cells[2].text.strip()
                    comment_text = cells[3].find('b').text.strip()
                    
                    # 日時をUnixタイムスタンプに変換
                    try:
                        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        timestamp = int(dt.timestamp())
                    except:
                        timestamp = 0
                    
                    comments.append({
                        "no": comment_no,
                        "date": timestamp,
                        "text": comment_text,
                        "elapsed_time": elapsed_time
                    })
            
            if not comments:
                continue
            
            # 開始時間をUnixタイムスタンプに変換
            try:
                start_dt = datetime.strptime(start_time_text, '%Y-%m-%d %H:%M:%S')
                start_timestamp = int(start_dt.timestamp())
            except:
                start_timestamp = 0
            
            # JSON形式のデータを構築
            json_data = {
                "broadcast_info": {
                    "lv_value": lv_value,
                    "start_time": start_timestamp,
                    "live_title": live_title
                },
                "user_info": {
                    "user_id": user_id,
                    "user_name": user_name
                },
                "total_count": len(comments),
                "comments": comments
            }
            
            # JSONファイルとして保存
            output_file = os.path.join(output_dir, f"{lv_value}_comments.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 変換完了: {lv_value} ({live_title}) - {len(comments)}コメント")
            converted_count += 1
            
        except Exception as e:
            print(f"❌ エラー: {str(e)}")
            continue
    
    print(f"\n📊 変換完了: {converted_count}個の配信データを変換しました")
    print(f"出力先: {output_dir}/")
    
    # 使用方法を表示
    print(f"\n💡 使用方法:")
    print(f"python import_comments_to_db.py --root-dir {output_dir}")

def create_directory_structure(base_dir: str, user_id: str, user_name: str):
    """SpecialUser形式のディレクトリ構造を作成"""
    
    special_user_dir = os.path.join(base_dir, "SpecialUser")
    user_dir = os.path.join(special_user_dir, f"{user_id}_{user_name}")
    
    os.makedirs(user_dir, exist_ok=True)
    
    return special_user_dir, user_dir

def convert_to_specialuser_format(json_dir: str, output_base: str = "SpecialUser_converted"):
    """JSONファイルをSpecialUser形式のディレクトリ構造に配置"""
    
    user_id = "21639740"
    user_name = "チンカスアニメ豚太郎"
    
    special_user_dir, user_dir = create_directory_structure(output_base, user_id, user_name)
    
    # JSONファイルを処理
    json_files = [f for f in os.listdir(json_dir) if f.endswith('_comments.json')]
    
    for json_file in json_files:
        json_path = os.path.join(json_dir, json_file)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        lv_value = data['broadcast_info']['lv_value']
        lv_dir = os.path.join(user_dir, lv_value)
        os.makedirs(lv_dir, exist_ok=True)
        
        # comments.jsonとして保存
        output_path = os.path.join(lv_dir, 'comments.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"📁 配置完了: {lv_value}")
    
    print(f"\n✅ SpecialUser形式での配置完了")
    print(f"出力先: {output_base}/")
    print(f"\n💡 インポート方法:")
    print(f"python import_comments_to_db.py --root-dir {output_base}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='HTMLからコメントデータをJSON形式に変換')
    parser.add_argument('html_file', help='入力HTMLファイルパス')
    parser.add_argument('--output-dir', default='converted_data', help='出力ディレクトリ')
    parser.add_argument('--create-specialuser', action='store_true', 
                        help='SpecialUser形式のディレクトリ構造も作成')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.html_file):
        print(f"❌ HTMLファイルが見つかりません: {args.html_file}")
        exit(1)
    
    print(f"🔄 HTMLファイルを解析中: {args.html_file}")
    
    # JSON形式に変換
    parse_html_to_json(args.html_file, args.output_dir)
    
    # SpecialUser形式も作成する場合
    if args.create_specialuser:
        print(f"\n🔄 SpecialUser形式のディレクトリ構造を作成中...")
        convert_to_specialuser_format(args.output_dir)