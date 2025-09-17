# processors/step04_database_storage.py
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any

class DatabaseManager:
    def __init__(self, db_path="data/ncv_monitor.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """データベースとテーブルを初期化"""
        with sqlite3.connect(self.db_path) as conn:
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
                
                -- 全コメントテーブル（監視ユーザー以外も含む）
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
                    tags TEXT, -- JSON配列として保存
                    template_name TEXT DEFAULT 'user_detail.html',
                    send_message TEXT, -- comment_system.py用のメッセージテンプレート
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
                
                -- 設定変更履歴
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    field_name TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by TEXT, -- 変更者（システム/手動）
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES special_users (user_id)
                );
                
                -- システム統計（容量監視用）
                CREATE TABLE IF NOT EXISTS system_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stat_date DATE,
                    total_broadcasts INTEGER,
                    total_comments INTEGER,
                    total_special_users INTEGER,
                    total_ai_analyses INTEGER,
                    db_size_mb REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- 検索用インデックス
                CREATE INDEX IF NOT EXISTS idx_comments_broadcast_user 
                    ON comments(broadcast_id, user_id);
                CREATE INDEX IF NOT EXISTS idx_comments_timestamp 
                    ON comments(timestamp);
                CREATE INDEX IF NOT EXISTS idx_comments_special_user 
                    ON comments(is_special_user);
                CREATE INDEX IF NOT EXISTS idx_comments_text_search 
                    ON comments(comment_text);
                CREATE INDEX IF NOT EXISTS idx_ai_analyses_broadcast_user 
                    ON ai_analyses(broadcast_id, user_id);
                CREATE INDEX IF NOT EXISTS idx_ai_analyses_date 
                    ON ai_analyses(analysis_date);
                CREATE INDEX IF NOT EXISTS idx_broadcasts_lv_value 
                    ON broadcasts(lv_value);
                CREATE INDEX IF NOT EXISTS idx_broadcasts_start_time 
                    ON broadcasts(start_time);
            ''')
        print(f"データベース初期化完了: {self.db_path}")

def process(pipeline_data):
    """Step04: データベース保存"""
    try:
        lv_value = pipeline_data['lv_value']
        config = pipeline_data['config']
        
        # Step01, Step02の結果を取得
        step01_results = pipeline_data['results']['step01_xml_parser']
        step02_results = pipeline_data['results']['step02_special_user_filter']
        
        broadcast_info = step01_results['broadcast_info']
        all_comments = step01_results['comments_data']
        special_users_found = step02_results['found_users']
        
        print(f"Step04 開始: データベース保存 - {lv_value}")
        print(f"[DEBUG] 保存対象: 放送1件, コメント{len(all_comments)}件, 特別ユーザー{len(special_users_found)}人")
        
        # データベースマネージャーを初期化
        db_manager = DatabaseManager()
        
        # 1. 放送情報を保存
        broadcast_id = save_broadcast_info(db_manager, lv_value, broadcast_info, pipeline_data)
        
        # 2. スペシャルユーザー設定を保存/更新
        save_special_users_config(db_manager, config)
        
        # 3. 全コメントを保存（コンテキスト用）
        comments_saved = save_all_comments(db_manager, broadcast_id, all_comments, special_users_found)
        
        # 4. AI分析結果を保存
        analyses_saved = save_ai_analyses(db_manager, broadcast_id, special_users_found)
        
        # 5. システム統計を更新
        update_system_stats(db_manager)
        
        print(f"Step04 完了: DB保存完了 - {lv_value}")
        print(f"[DEBUG] 保存済み: 放送ID={broadcast_id}, コメント{comments_saved}件, AI分析{analyses_saved}件")
        
        return {
            "database_saved": True,
            "broadcast_id": broadcast_id,
            "total_comments_saved": comments_saved,
            "special_users_saved": len(special_users_found),
            "ai_analyses_saved": analyses_saved,
            "db_path": db_manager.db_path
        }
        
    except Exception as e:
        print(f"Step04 エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def save_broadcast_info(db_manager: DatabaseManager, lv_value: str, 
                       broadcast_info: Dict, pipeline_data: Dict) -> int:
    """放送情報をデータベースに保存"""
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        # 既存の放送があるかチェック
        cursor.execute("SELECT id FROM broadcasts WHERE lv_value = ?", (lv_value,))
        existing = cursor.fetchone()
        
        if existing:
            broadcast_id = existing[0]
            # 既存放送を更新
            cursor.execute('''
                UPDATE broadcasts 
                SET live_title = ?, broadcaster = ?, community_name = ?, 
                    start_time = ?, end_time = ?, watch_count = ?, comment_count = ?, 
                    owner_id = ?, owner_name = ?, subfolder_name = ?, xml_path = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE lv_value = ?
            ''', (
                broadcast_info.get('live_title', ''),
                broadcast_info.get('broadcaster', ''),
                broadcast_info.get('community_name', ''),
                safe_int(broadcast_info.get('start_time', 0)),
                safe_int(broadcast_info.get('end_time', 0)),
                safe_int(broadcast_info.get('watch_count', 0)),
                safe_int(broadcast_info.get('comment_count', 0)),
                broadcast_info.get('owner_id', ''),
                broadcast_info.get('owner_name', ''),
                pipeline_data.get('subfolder_name', ''),
                pipeline_data.get('xml_path', ''),
                lv_value
            ))
            print(f"既存の放送を更新: {lv_value} (ID: {broadcast_id})")
        else:
            # 新規放送として挿入
            cursor.execute('''
                INSERT INTO broadcasts 
                (lv_value, live_title, broadcaster, community_name, start_time, 
                 end_time, watch_count, comment_count, owner_id, owner_name, 
                 subfolder_name, xml_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                lv_value,
                broadcast_info.get('live_title', ''),
                broadcast_info.get('broadcaster', ''),
                broadcast_info.get('community_name', ''),
                safe_int(broadcast_info.get('start_time', 0)),
                safe_int(broadcast_info.get('end_time', 0)),
                safe_int(broadcast_info.get('watch_count', 0)),
                safe_int(broadcast_info.get('comment_count', 0)),
                broadcast_info.get('owner_id', ''),
                broadcast_info.get('owner_name', ''),
                pipeline_data.get('subfolder_name', ''),
                pipeline_data.get('xml_path', '')
            ))
            broadcast_id = cursor.lastrowid
            print(f"新規放送を保存: {lv_value} (ID: {broadcast_id})")
        
        return broadcast_id

def save_special_users_config(db_manager: DatabaseManager, config: Dict):
    """スペシャルユーザー設定を保存/更新"""
    special_users_config = config.get("special_users_config", {})
    users = special_users_config.get("users", {})
    
    if not users:
        print("スペシャルユーザー設定が空です")
        return
    
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        for user_id, user_config in users.items():
            # 既存ユーザーをチェック
            cursor.execute("""
                SELECT custom_prompt, ai_model, analysis_enabled, display_name 
                FROM special_users WHERE user_id = ?
            """, (user_id,))
            existing = cursor.fetchone()
            
            current_prompt = user_config.get('analysis_prompt', '')
            current_model = user_config.get('analysis_ai_model', 'openai-gpt4o')
            current_enabled = user_config.get('analysis_enabled', True)
            current_name = user_config.get('display_name', f'ユーザー{user_id}')
            tags_json = json.dumps(user_config.get('tags', []))
            send_message = user_config.get('send_message', '')
            
            if existing:
                # 既存ユーザーを更新
                old_prompt, old_model, old_enabled, old_name = existing
                
                cursor.execute('''
                    UPDATE special_users 
                    SET display_name = ?, analysis_enabled = ?, ai_model = ?, 
                        custom_prompt = ?, description = ?, tags = ?, 
                        template_name = ?, send_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (
                    current_name,
                    current_enabled,
                    current_model,
                    current_prompt,
                    user_config.get('description', ''),
                    tags_json,
                    user_config.get('template', 'user_detail.html'),
                    send_message,
                    user_id
                ))
                
                # 変更があれば履歴に記録
                changes = []
                if old_prompt != current_prompt:
                    changes.append(('custom_prompt', old_prompt, current_prompt))
                if old_model != current_model:
                    changes.append(('ai_model', old_model, current_model))
                if old_enabled != current_enabled:
                    changes.append(('analysis_enabled', str(old_enabled), str(current_enabled)))
                if old_name != current_name:
                    changes.append(('display_name', old_name, current_name))
                
                for field_name, old_value, new_value in changes:
                    cursor.execute('''
                        INSERT INTO config_history (user_id, field_name, old_value, new_value, changed_by)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, field_name, old_value, new_value, 'system'))
                    
                if changes:
                    print(f"ユーザー設定更新: {user_id} ({len(changes)}項目変更)")
                    
            else:
                # 新規ユーザーを挿入
                cursor.execute('''
                    INSERT INTO special_users 
                    (user_id, display_name, analysis_enabled, ai_model, custom_prompt, 
                     description, tags, template_name, send_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    current_name,
                    current_enabled,
                    current_model,
                    current_prompt,
                    user_config.get('description', ''),
                    tags_json,
                    user_config.get('template', 'user_detail.html'),
                    send_message
                ))
                print(f"新規スペシャルユーザー登録: {user_id} ({current_name})")

def save_all_comments(db_manager: DatabaseManager, broadcast_id: int, 
                     all_comments: List[Dict], special_users_found: List[Dict]) -> int:
    """全コメントを保存（コンテキスト用）"""
    special_user_ids = {user['user_id'] for user in special_users_found}
    
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        # 既存コメントを削除（重複回避）
        cursor.execute("DELETE FROM comments WHERE broadcast_id = ?", (broadcast_id,))
        
        if not all_comments:
            print("保存するコメントがありません")
            return 0
        
        # 配信開始時刻を取得（経過時間計算用）
        start_timestamp = all_comments[0].get('date', 0) if all_comments else 0
        
        # 全コメントを一括挿入
        comment_data = []
        for comment in all_comments:
            user_id = comment.get('user_id', '')
            is_special = user_id in special_user_ids
            
            # 配信開始からの経過時間を計算
            elapsed_time = calculate_elapsed_time(
                comment.get('date', 0), 
                start_timestamp
            )
            
            comment_data.append((
                broadcast_id,
                user_id,
                comment.get('user_name', ''),
                comment.get('text', ''),
                safe_int(comment.get('no', 0)),
                safe_int(comment.get('date', 0)),
                elapsed_time,
                is_special,
                safe_int(comment.get('premium', 0)),
                bool(comment.get('anonymity', False))
            ))
        
        cursor.executemany('''
            INSERT INTO comments 
            (broadcast_id, user_id, user_name, comment_text, comment_no, 
             timestamp, elapsed_time, is_special_user, premium, anonymity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', comment_data)
        
        comments_saved = len(comment_data)
        special_comments = sum(1 for _, user_id, *_ in comment_data if user_id in special_user_ids)
        
        print(f"全コメント保存完了: {comments_saved}件 (特別ユーザー: {special_comments}件)")
        return comments_saved

def save_ai_analyses(db_manager: DatabaseManager, broadcast_id: int, 
                    special_users_found: List[Dict]) -> int:
    """AI分析結果を保存"""
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        analyses_saved = 0
        
        for user_data in special_users_found:
            user_id = user_data['user_id']
            ai_analysis = user_data.get('ai_analysis', '')
            ai_model_used = user_data.get('ai_model_used', 'unknown')
            ai_prompt_used = user_data.get('ai_prompt_used', '')
            
            if not ai_analysis:
                print(f"AI分析結果が空です: {user_id}")
                continue
            
            # 既存の分析結果があるかチェック
            cursor.execute("""
                SELECT id FROM ai_analyses 
                WHERE broadcast_id = ? AND user_id = ?
            """, (broadcast_id, user_id))
            existing = cursor.fetchone()
            
            if existing:
                # 既存の分析結果を更新
                cursor.execute('''
                    UPDATE ai_analyses 
                    SET model_used = ?, prompt_used = ?, analysis_result = ?, 
                        comment_count = ?, analysis_date = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    ai_model_used,
                    ai_prompt_used,
                    ai_analysis,
                    len(user_data.get('comments', [])),
                    existing[0]
                ))
                print(f"AI分析結果更新: {user_id} (モデル: {ai_model_used})")
            else:
                # 新規の分析結果を挿入
                cursor.execute('''
                    INSERT INTO ai_analyses 
                    (broadcast_id, user_id, model_used, prompt_used, analysis_result, comment_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    broadcast_id,
                    user_id,
                    ai_model_used,
                    ai_prompt_used,
                    ai_analysis,
                    len(user_data.get('comments', []))
                ))
                print(f"AI分析結果保存: {user_id} (モデル: {ai_model_used})")
            
            analyses_saved += 1
        
        return analyses_saved

def update_system_stats(db_manager: DatabaseManager):
    """システム統計を更新"""
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # 各テーブルの件数を取得
            cursor.execute("SELECT COUNT(*) FROM broadcasts")
            total_broadcasts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM comments")
            total_comments = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM special_users")
            total_special_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ai_analyses")
            total_ai_analyses = cursor.fetchone()[0]
            
            # DBファイルサイズを取得
            db_size_mb = os.path.getsize(db_manager.db_path) / (1024 * 1024)
            
            # 今日の統計があるかチェック
            today = datetime.now().date()
            cursor.execute("SELECT id FROM system_stats WHERE stat_date = ?", (today,))
            existing = cursor.fetchone()
            
            if existing:
                # 今日の統計を更新
                cursor.execute('''
                    UPDATE system_stats 
                    SET total_broadcasts = ?, total_comments = ?, total_special_users = ?, 
                        total_ai_analyses = ?, db_size_mb = ?
                    WHERE stat_date = ?
                ''', (total_broadcasts, total_comments, total_special_users, 
                      total_ai_analyses, db_size_mb, today))
            else:
                # 新規統計を挿入
                cursor.execute('''
                    INSERT INTO system_stats 
                    (stat_date, total_broadcasts, total_comments, total_special_users, 
                     total_ai_analyses, db_size_mb)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (today, total_broadcasts, total_comments, total_special_users, 
                      total_ai_analyses, db_size_mb))
            
            print(f"システム統計更新: 放送{total_broadcasts}件, コメント{total_comments}件, DB容量{db_size_mb:.1f}MB")
            
    except Exception as e:
        print(f"システム統計更新エラー: {str(e)}")

def calculate_elapsed_time(comment_timestamp: int, start_timestamp: int) -> str:
    """コメント時刻から配信開始からの経過時間を計算"""
    try:
        elapsed_seconds = safe_int(comment_timestamp) - safe_int(start_timestamp)
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

# データベース検索・取得用のヘルパー関数

def get_broadcast_by_lv(db_path: str, lv_value: str) -> Dict:
    """lv値で放送情報を取得"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM broadcasts WHERE lv_value = ?
        """, (lv_value,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
    return {}

def get_comments_by_broadcast(db_path: str, broadcast_id: int, special_only: bool = False) -> List[Dict]:
    """放送IDでコメントを取得"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT * FROM comments WHERE broadcast_id = ?
        """
        params = [broadcast_id]
        
        if special_only:
            query += " AND is_special_user = 1"
        
        query += " ORDER BY timestamp"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

def get_user_analysis_history(db_path: str, user_id: str) -> List[Dict]:
    """ユーザーのAI分析履歴を取得"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, b.lv_value, b.live_title, b.start_time
            FROM ai_analyses a
            JOIN broadcasts b ON a.broadcast_id = b.id
            WHERE a.user_id = ?
            ORDER BY a.analysis_date DESC
        """, (user_id,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

def search_comments_by_text(db_path: str, search_text: str, limit: int = 100) -> List[Dict]:
    """コメント内容で検索"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, b.lv_value, b.live_title, b.start_time
            FROM comments c
            JOIN broadcasts b ON c.broadcast_id = b.id
            WHERE c.comment_text LIKE ?
            ORDER BY c.timestamp DESC
            LIMIT ?
        """, (f"%{search_text}%", limit))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]