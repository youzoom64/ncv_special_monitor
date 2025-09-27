#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSONファイルをDBに直接投入するスクリプト
"""

import os
import json
import sqlite3
from processors.step04_database_storage import DatabaseManager

def import_json_files_to_db(json_dir: str, db_path: str = "data/ncv_monitor.db"):
    """JSONファイルをDBに投入"""
    
    db_manager = DatabaseManager(db_path)
    
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    
    total_broadcasts = 0
    total_comments = 0
    
    for json_file in json_files:
        json_path = os.path.join(json_dir, json_file)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 放送情報を保存
        broadcast_id = save_broadcast(db_manager, data)
        
        # コメントを保存
        comments_saved = save_comments(db_manager, broadcast_id, data)
        
        total_broadcasts += 1
        total_comments += comments_saved
        
        print(f"投入完了: {data['broadcast_info']['lv_value']} - {comments_saved}コメント")
    
    print(f"全体完了: {total_broadcasts}配信, {total_comments}コメント")

def save_broadcast(db_manager: DatabaseManager, data):
    """放送データを保存"""
    
    broadcast_info = data['broadcast_info']
    user_info = data['user_info']
    
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM broadcasts WHERE lv_value = ?", 
                      (broadcast_info['lv_value'],))
        existing = cursor.fetchone()
        
        if existing:
            return existing[0]
        
        cursor.execute('''
            INSERT INTO broadcasts 
            (lv_value, live_title, broadcaster, start_time, comment_count, 
             owner_id, owner_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            broadcast_info['lv_value'],
            broadcast_info['live_title'],
            user_info['user_name'],
            broadcast_info['start_time'],
            data['total_count'],
            user_info['user_id'],
            user_info['user_name']
        ))
        
        return cursor.lastrowid

def save_comments(db_manager: DatabaseManager, broadcast_id: int, data):
    """コメントデータを保存"""
    
    comments = data['comments']
    user_info = data['user_info']
    
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        # 既存コメント削除
        cursor.execute("DELETE FROM comments WHERE broadcast_id = ?", (broadcast_id,))
        
        comment_data = []
        for comment in comments:
            comment_data.append((
                broadcast_id,
                user_info['user_id'],
                user_info['user_name'],
                comment['text'],
                comment['no'],
                comment['date'],
                comment.get('elapsed_time', '00:00:00'),
                False,  # is_special_user
                0,      # premium
                False   # anonymity
            ))
        
        cursor.executemany('''
            INSERT INTO comments 
            (broadcast_id, user_id, user_name, comment_text, comment_no, 
             timestamp, elapsed_time, is_special_user, premium, anonymity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', comment_data)
        
        return len(comment_data)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("使用法: python import_json_to_db.py <JSONディレクトリ>")
        sys.exit(1)
    
    json_dir = sys.argv[1]
    import_json_files_to_db(json_dir)