# import_comments_to_db.py（修正版）
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List

def init_database(db_path="data/ncv_monitor.db"):
    """データベースとテーブルを初期化"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        conn.executescript('''
            -- 放送テーブル
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lv_value TEXT UNIQUE NOT NULL,
                live_title TEXT,
                broadcaster TEXT,
                community_name TEXT,
                start_time INTEGER,
                end_time INTEGER,
                watch_count INTEGER,
                comment_count INTEGER,
                owner_id TEXT,
                owner_name TEXT,
                subfolder_name TEXT,
                xml_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- コメントテーブル
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_id INTEGER,
                user_id TEXT NOT NULL,
                user_name TEXT,
                comment_text TEXT,
                comment_no INTEGER,
                timestamp INTEGER,
                elapsed_time TEXT,
                is_special_user BOOLEAN DEFAULT FALSE,
                premium INTEGER DEFAULT 0,
                anonymity BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (broadcast_id) REFERENCES broadcasts (id)
            );
            
            -- 監視ユーザー設定
            CREATE TABLE IF NOT EXISTS special_users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                analysis_enabled BOOLEAN DEFAULT TRUE,
                ai_model TEXT DEFAULT 'openai-gpt4o',
                custom_prompt TEXT,
                description TEXT,
                tags TEXT,
                template_name TEXT DEFAULT 'user_detail.html',
                send_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- AI分析結果
            CREATE TABLE IF NOT EXISTS ai_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_id INTEGER,
                user_id TEXT,
                model_used TEXT,
                prompt_used TEXT,
                analysis_result TEXT,
                comment_count INTEGER,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_seconds REAL,
                token_usage INTEGER,
                FOREIGN KEY (broadcast_id) REFERENCES broadcasts (id),
                FOREIGN KEY (user_id) REFERENCES special_users (user_id)
            );
            
            -- インデックス
            CREATE INDEX IF NOT EXISTS idx_comments_broadcast_user ON comments(broadcast_id, user_id);
            CREATE INDEX IF NOT EXISTS idx_comments_timestamp ON comments(timestamp);
            CREATE INDEX IF NOT EXISTS idx_comments_special_user ON comments(is_special_user);
            CREATE INDEX IF NOT EXISTS idx_broadcasts_lv_value ON broadcasts(lv_value);
        ''')
    print(f"データベース初期化完了: {db_path}")

def find_all_comments_json(root_directory="./"):
    """SpecialUserフォルダ内の全comments.jsonファイルを検索"""
    comments_files = []
    
    special_user_dir = os.path.join(root_directory, "SpecialUser")
    if not os.path.exists(special_user_dir):
        print(f"SpecialUserディレクトリが見つかりません: {special_user_dir}")
        return comments_files
    
    # パターン1: SpecialUser/{user_id}_{name}/lv{id}/comments.json
    # パターン2: SpecialUser/BroadCastData/{user_id}_{name}/lv{id}/comments.json
    
    for root, dirs, files in os.walk(special_user_dir):
        if "comments.json" in files:
            comments_path = os.path.join(root, "comments.json")
            
            # パスから情報を抽出
            path_parts = root.replace(special_user_dir, "").strip(os.sep).split(os.sep)
            
            if len(path_parts) >= 2:
                # lv番号を取得
                lv_folder = path_parts[-1]
                if lv_folder.startswith('lv'):
                    # ユーザー情報を取得
                    if "BroadCastData" in path_parts:
                        # パターン2: BroadCastData/{user_id}_{name}/lv{id}/
                        user_folder = path_parts[-2]
                        data_type = "broadcaster"
                    else:
                        # パターン1: {user_id}_{name}/lv{id}/
                        user_folder = path_parts[-2]
                        data_type = "viewer"
                    
                    comments_files.append({
                        'path': comments_path,
                        'lv_value': lv_folder,
                        'user_folder': user_folder,
                        'data_type': data_type,
                        'relative_path': os.path.relpath(comments_path, root_directory)
                    })
    
    return comments_files

def import_comments_from_json(root_directory="./", db_path="data/ncv_monitor.db"):
    """SpecialUserフォルダ内の全comments.jsonからDBにデータをインポート"""
    
    # データベース初期化
    init_database(db_path)
    
    # 全comments.jsonファイルを検索
    comments_files = find_all_comments_json(root_directory)
    
    if not comments_files:
        print("comments.jsonファイルが見つかりませんでした")
        return
    
    print(f"見つかったcomments.json: {len(comments_files)}件")
    
    total_broadcasts = 0
    total_comments = 0
    
    for file_info in comments_files:
        try:
            # comments.jsonを読み込み
            with open(file_info['path'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # データをDBに保存
            broadcast_id = save_broadcast_data(db_path, file_info, data)
            comments_saved = save_comments_data(db_path, broadcast_id, data, file_info)  # file_info追加
            
            total_broadcasts += 1
            total_comments += comments_saved
            
            print(f"✅ {file_info['relative_path']}: 放送ID={broadcast_id}, コメント{comments_saved}件 ({file_info['data_type']})")
            
        except Exception as e:
            print(f"❌ {file_info['relative_path']}: エラー - {str(e)}")
    
    print(f"\n📊 インポート完了: 放送{total_broadcasts}件, コメント{total_comments}件")

def save_broadcast_data(db_path: str, file_info: Dict, data) -> int:
    """放送データを保存（両方の形式に対応）"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        lv_value = file_info['lv_value']
        
        if file_info['data_type'] == 'broadcaster':
            # BroadCastData形式: 配列から情報を推定
            user_folder = file_info['user_folder']
            broadcaster_id = user_folder.split('_')[0] if '_' in user_folder else ''
            broadcaster_name = user_folder.split('_', 1)[1] if '_' in user_folder else ''
            
            # 配信開始時刻を推定（最初のコメント時刻）
            start_time = 0
            comment_count = 0
            if isinstance(data, list) and data:
                timestamps = [safe_int(c.get('date', 0)) for c in data if c.get('date')]
                if timestamps:
                    start_time = min(timestamps)
                comment_count = len(data)
            
        else:
            # SpecialUser形式: 既存のロジック
            broadcast_info = data.get('broadcast_info', {})
            user_info = data.get('user_info', {})
            broadcaster_name = user_info.get('user_name', '')
            start_time = safe_int(broadcast_info.get('start_time', 0))
            comment_count = data.get('total_count', 0)
        
        # 既存の放送があるかチェック
        cursor.execute("SELECT id FROM broadcasts WHERE lv_value = ?", (lv_value,))
        existing = cursor.fetchone()
        
        if existing:
            broadcast_id = existing[0]
            # 既存放送の情報を更新
            cursor.execute('''
                UPDATE broadcasts 
                SET broadcaster = COALESCE(NULLIF(broadcaster, ''), ?),
                    owner_name = COALESCE(NULLIF(owner_name, ''), ?),
                    start_time = COALESCE(NULLIF(start_time, 0), ?),
                    comment_count = comment_count + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE lv_value = ?
            ''', (broadcaster_name, broadcaster_name, start_time, comment_count, lv_value))
        else:
            # 新規放送として挿入
            cursor.execute('''
                INSERT INTO broadcasts 
                (lv_value, broadcaster, owner_name, start_time, comment_count, subfolder_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (lv_value, broadcaster_name, broadcaster_name, start_time, comment_count, file_info['user_folder']))
            broadcast_id = cursor.lastrowid
        
        return broadcast_id

def save_comments_data(db_path: str, broadcast_id: int, data: Dict, file_info: Dict) -> int:
    """コメントデータを保存（両方の形式に対応）"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # データ形式を判定
        if file_info['data_type'] == 'broadcaster':
            # BroadCastData形式: 直接配列
            comments = data if isinstance(data, list) else []
            
            # ファイルパスからlv値と配信者情報を抽出
            lv_value = file_info['lv_value']
            user_folder = file_info['user_folder']
            broadcaster_id = user_folder.split('_')[0] if '_' in user_folder else ''
            broadcaster_name = user_folder.split('_', 1)[1] if '_' in user_folder else ''
            
            # 配信開始時刻を推定（最初のコメント時刻）
            start_timestamp = min(safe_int(c.get('date', 0)) for c in comments) if comments else 0
            
            # この放送の既存コメントを削除
            cursor.execute('DELETE FROM comments WHERE broadcast_id = ?', (broadcast_id,))
            
        else:
            # SpecialUser形式: 既存のロジック
            comments = data.get('comments', [])
            user_info = data.get('user_info', {})
            broadcast_info = data.get('broadcast_info', {})
            start_timestamp = safe_int(broadcast_info.get('start_time', 0))
            user_id = user_info.get('user_id', '')
            
            # この放送・ユーザーの既存コメントを削除
            cursor.execute('''
                DELETE FROM comments 
                WHERE broadcast_id = ? AND user_id = ?
            ''', (broadcast_id, user_id))
        
        if not comments:
            return 0
        
        # コメントデータを準備
        comment_data = []
        for comment in comments:
            comment_timestamp = safe_int(comment.get('date', 0))
            elapsed_time = calculate_elapsed_time(comment_timestamp, start_timestamp)
            
            if file_info['data_type'] == 'broadcaster':
                # BroadCastData形式
                comment_user_id = comment.get('user_id', '')
                comment_user_name = comment.get('user_name', '')
            else:
                # SpecialUser形式
                comment_user_id = user_id
                comment_user_name = comment.get('name', user_info.get('user_name', ''))
            
            comment_data.append((
                broadcast_id,
                comment_user_id,
                comment_user_name,
                comment.get('text', ''),
                safe_int(comment.get('no', 0)),
                comment_timestamp,
                elapsed_time,
                False,  # is_special_user（後で設定）
                safe_int(comment.get('premium', 0)),
                bool(comment.get('anonymity', False))
            ))
        
        # 一括挿入
        cursor.executemany('''
            INSERT INTO comments 
            (broadcast_id, user_id, user_name, comment_text, comment_no, 
             timestamp, elapsed_time, is_special_user, premium, anonymity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', comment_data)
        
        return len(comment_data)

def calculate_elapsed_time(comment_timestamp: int, start_timestamp: int) -> str:
    """経過時間を計算"""
    try:
        elapsed_seconds = comment_timestamp - start_timestamp
        if elapsed_seconds < 0:
            elapsed_seconds = 0
        
        hours = elapsed_seconds // 3600
        minutes = (elapsed_seconds % 3600) // 60
        seconds = elapsed_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except:
        return "00:00:00"

def safe_int(value) -> int:
    """安全に整数に変換"""
    try:
        if value is None or value == '':
            return 0
        return int(value)
    except (ValueError, TypeError):
        return 0

def mark_special_users(db_path: str, special_user_ids: List[str]):
    """指定したユーザーIDをスペシャルユーザーとしてマーク"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        for user_id in special_user_ids:
            # special_usersテーブルに登録
            cursor.execute('''
                INSERT OR IGNORE INTO special_users (user_id, display_name)
                VALUES (?, ?)
            ''', (user_id, f"ユーザー{user_id}"))
            
            # commentsテーブルでis_special_userをTrueに
            cursor.execute('''
                UPDATE comments SET is_special_user = TRUE WHERE user_id = ?
            ''', (user_id,))
        
        print(f"スペシャルユーザー設定完了: {len(special_user_ids)}人")

def debug_directory_structure(root_directory="./"):
    """ディレクトリ構造をデバッグ表示"""
    print(f"ルートディレクトリ: {os.path.abspath(root_directory)}")
    
    special_user_dir = os.path.join(root_directory, "SpecialUser")
    print(f"SpecialUserディレクトリ: {special_user_dir}")
    
    if os.path.exists(special_user_dir):
        comments_files = find_all_comments_json(root_directory)
        print(f"見つかったcomments.json: {len(comments_files)}件")
        
        for file_info in comments_files:
            print(f"  {file_info['relative_path']} ({file_info['data_type']})")
    else:
        print("SpecialUserディレクトリが存在しません")

def auto_detect_special_users(root_directory="./"):
    """SpecialUserフォルダ構造からスペシャルユーザーを自動検出"""
    special_user_ids = set()
    
    special_user_dir = os.path.join(root_directory, "SpecialUser")
    if not os.path.exists(special_user_dir):
        return list(special_user_ids)
    
    # SpecialUser直下のフォルダを検索（BroadCastDataは除外）
    for item in os.listdir(special_user_dir):
        item_path = os.path.join(special_user_dir, item)
        if os.path.isdir(item_path) and item != "BroadCastData":
            # {user_id}_{name} 形式からuser_idを抽出
            if '_' in item:
                user_id = item.split('_')[0]
                special_user_ids.add(user_id)
    
    return list(special_user_ids)

# main関数を修正
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='SpecialUserフォルダのcomments.jsonからDBにインポート')
    parser.add_argument('--root-dir', default='./', help='ルートディレクトリ')
    parser.add_argument('--db-path', default='data/ncv_monitor.db', help='データベースパス')
    parser.add_argument('--special-users', nargs='*', default=None, help='追加のスペシャルユーザーID')
    parser.add_argument('--debug', action='store_true', help='ディレクトリ構造をデバッグ表示')
    
    args = parser.parse_args()
    
    print("📥 SpecialUserフォルダからDBインポート開始")
    
    if args.debug:
        debug_directory_structure(args.root_dir)
        exit()
    
    # データインポート
    import_comments_from_json(args.root_dir, args.db_path)
    
    # スペシャルユーザーを自動検出
    auto_detected_users = auto_detect_special_users(args.root_dir)
    
    # 手動指定ユーザーと合併
    all_special_users = set(auto_detected_users)
    if args.special_users:
        all_special_users.update(args.special_users)
    
    if all_special_users:
        print(f"スペシャルユーザー検出: {list(all_special_users)}")
        mark_special_users(args.db_path, list(all_special_users))
    
    print("✅ インポート完了")