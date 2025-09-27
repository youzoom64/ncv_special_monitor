import sqlite3
import json
import os

CONFIG = {
    "json_file": "comments.json",
    "db_path": "data/ncv_monitor.db",
    "encoding": "utf-8"
}

def debuglog(msg):
    print(f"[DEBUG] {msg}", flush=True)

def alter_database():
    """既存のcommentsテーブルに新しいカラムを追加"""
    with sqlite3.connect(CONFIG["db_path"]) as conn:
        cursor = conn.cursor()
        
        # 既存カラムをチェック
        cursor.execute("PRAGMA table_info(comments)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # 新しいカラムを追加
        if 'broadcast_title' not in existing_columns:
            cursor.execute('ALTER TABLE comments ADD COLUMN broadcast_title TEXT')
            debuglog("broadcast_title カラムを追加")
        
        if 'broadcast_start_time' not in existing_columns:
            cursor.execute('ALTER TABLE comments ADD COLUMN broadcast_start_time TEXT')
            debuglog("broadcast_start_time カラムを追加")
            
        if 'broadcast_lv_id' not in existing_columns:
            cursor.execute('ALTER TABLE comments ADD COLUMN broadcast_lv_id TEXT')
            debuglog("broadcast_lv_id カラムを追加")

def load_json_data():
    """JSONファイルを読み込み"""
    with open(CONFIG["json_file"], 'r', encoding=CONFIG["encoding"]) as f:
        data = json.load(f)
    return data

def save_to_database(comments_data):
    """JSONデータをデータベースに保存（上書き）"""
    with sqlite3.connect(CONFIG["db_path"]) as conn:
        cursor = conn.cursor()
        
        saved_count = 0
        broadcast_ids = {}
        
        for comment in comments_data:
            lv_value = comment["lv_value"]
            
            # 放送情報を保存/取得
            if lv_value not in broadcast_ids:
                cursor.execute("SELECT id FROM broadcasts WHERE lv_value = ?", (lv_value,))
                existing_broadcast = cursor.fetchone()
                
                if existing_broadcast:
                    broadcast_id = existing_broadcast[0]
                    # 既存放送のタイトルを更新
                    cursor.execute('''
                        UPDATE broadcasts 
                        SET live_title = ?, start_time = ?
                        WHERE lv_value = ?
                    ''', (
                        comment.get("live_title", ""),
                        comment.get("timestamp", 0),
                        lv_value
                    ))
                    debuglog(f"既存放送更新: {lv_value} (ID: {broadcast_id})")
                else:
                    cursor.execute('''
                        INSERT INTO broadcasts (lv_value, live_title, broadcaster, start_time)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        lv_value,
                        comment.get("live_title", ""),
                        "",
                        comment.get("timestamp", 0)
                    ))
                    broadcast_id = cursor.lastrowid
                    debuglog(f"新規放送登録: {lv_value} (ID: {broadcast_id})")
                
                broadcast_ids[lv_value] = broadcast_id
            else:
                broadcast_id = broadcast_ids[lv_value]
            
            # 上書き保存（INSERT OR REPLACE）
            cursor.execute('''
                INSERT OR REPLACE INTO comments 
                (broadcast_id, user_id, user_name, comment_text, comment_no, 
                 timestamp, elapsed_time, is_special_user, premium, anonymity,
                 broadcast_title, broadcast_start_time, broadcast_lv_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                broadcast_id,
                comment.get("user_id"),
                comment["user_name"],
                comment["comment_text"],
                comment["comment_no"],
                comment.get("timestamp", 0),
                comment["elapsed_time"],
                1,  # is_special_user
                0,  # premium
                0,  # anonymity
                comment.get("live_title", ""),
                comment.get("start_time", ""),
                comment["lv_value"]
            ))
            saved_count += 1
        
        debuglog(f"DB保存完了: {saved_count}件のコメントを保存")
        return saved_count

def main():
    # JSONファイル存在確認
    if not os.path.exists(CONFIG["json_file"]):
        debuglog(f"JSONファイルが見つかりません: {CONFIG['json_file']}")
        return
    
    # データベースのカラム追加
    alter_database()
    
    # JSONデータ読み込み
    comments_data = load_json_data()
    debuglog(f"JSONファイル読み込み完了: {len(comments_data)}件")
    
    # データベース保存
    saved_count = save_to_database(comments_data)
    debuglog(f"データベース保存完了: {CONFIG['db_path']}")
    debuglog(f"保存されたコメント数: {saved_count}")
    
    # 統計表示
    with sqlite3.connect(CONFIG["db_path"]) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM broadcasts")
        total_broadcasts = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM comments WHERE user_name = ?", ("チンカスアニメ豚太郎",))
        total_comments = cursor.fetchone()[0]
        
        debuglog(f"データベース統計: 放送{total_broadcasts}件, チンカスアニメ豚太郎のコメント{total_comments}件")

if __name__ == "__main__":
    main()