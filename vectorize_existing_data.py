# vectorize_existing_data.py（修正版）
import sqlite3
import numpy as np
import os
import time
from typing import List, Dict
import json

class VectorizationManager:
    def __init__(self, db_path="data/ncv_monitor.db", vector_db_path="data/vectors.db"):
        self.db_path = db_path
        self.vector_db_path = vector_db_path
        self.init_vector_db()
    
    def init_vector_db(self):
        """ベクトルデータベース初期化"""
        os.makedirs(os.path.dirname(self.vector_db_path), exist_ok=True)
        
        with sqlite3.connect(self.vector_db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS comment_vectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broadcast_id INTEGER,
                    comment_id INTEGER UNIQUE,
                    user_id TEXT,
                    comment_text TEXT,
                    vector_data BLOB,
                    embedding_model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS analysis_vectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broadcast_id INTEGER,
                    analysis_id INTEGER UNIQUE,
                    user_id TEXT,
                    analysis_text TEXT,
                    vector_data BLOB,
                    embedding_model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_comment_vectors_broadcast ON comment_vectors(broadcast_id);
                CREATE INDEX IF NOT EXISTS idx_analysis_vectors_broadcast ON analysis_vectors(broadcast_id);
            ''')
            conn.commit()  # 明示的にコミット
        print(f"ベクトルDB初期化完了: {self.vector_db_path}")
    
    def vectorize_all_special_users(self, limit=None):
        """全スペシャルユーザーのコメントをベクトル化"""
        
        # 未処理のスペシャルユーザーコメントを取得
        with sqlite3.connect(self.db_path) as main_conn:
            cursor = main_conn.cursor()
            
            # まずはシンプルにスペシャルユーザーのコメントを取得
            query = """
                SELECT c.id, c.broadcast_id, c.user_id, c.comment_text, c.user_name
                FROM comments c
                WHERE c.is_special_user = 1
                AND c.comment_text != ''
                AND LENGTH(c.comment_text) > 3
                ORDER BY c.timestamp
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            all_comments = cursor.fetchall()
        
        # 既にベクトル化済みのコメントIDを取得
        vectorized_ids = set()
        try:
            with sqlite3.connect(self.vector_db_path) as vector_conn:
                cursor = vector_conn.cursor()
                cursor.execute("SELECT comment_id FROM comment_vectors")
                vectorized_ids = {row[0] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            # テーブルが存在しない場合は空のセット
            vectorized_ids = set()
        
        # 未ベクトル化のコメントをフィルタリング
        comments = [c for c in all_comments if c[0] not in vectorized_ids]
        
        print(f"ベクトル化対象: {len(comments)}件のスペシャルユーザーコメント")
        
        if not comments:
            print("ベクトル化する新規コメントがありません")
            return 0
        
        vectors_saved = 0
        
        for i, (comment_id, broadcast_id, user_id, comment_text, user_name) in enumerate(comments, 1):
            print(f"[{i}/{len(comments)}] 処理中: {user_name} - {comment_text[:30]}...")
            
            vector = self._get_embedding(comment_text)
            if vector is not None:
                if self._save_comment_vector(broadcast_id, comment_id, user_id, comment_text, vector):
                    vectors_saved += 1
            
            time.sleep(0.1)  # API制限対策
        
        print(f"完了: {vectors_saved}件のベクトルを保存")
        return vectors_saved
        
    def _get_embedding(self, text: str):
        """テキストをベクトル化"""
        try:
            import openai
            import json
            
            # 設定ファイルからAPIキーを取得
            api_key = self._get_api_key_from_config()
            if not api_key:
                # 環境変数からもフォールバック
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    print("OpenAI APIキーが設定されていません")
                    return None
            
            client = openai.OpenAI(api_key=api_key)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            return np.array(response.data[0].embedding, dtype=np.float32)
            
        except Exception as e:
            print(f"ベクトル化エラー: {str(e)}")
            return None
    
    def _get_api_key_from_config(self):
        """設定ファイルからOpenAI APIキーを取得"""
        config_path = "config/ncv_special_config.json"
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                api_key = config.get('api_settings', {}).get('openai_api_key', '')
                if api_key and api_key.strip():
                    return api_key.strip()
            
            print(f"設定ファイルにAPIキーが見つかりません: {config_path}")
            return None
            
        except Exception as e:
            print(f"設定ファイル読み取りエラー: {str(e)}")
            return None


    def _save_comment_vector(self, broadcast_id, comment_id, user_id, comment_text, vector):
        """コメントベクトルを保存"""
        try:
            with sqlite3.connect(self.vector_db_path) as conn:
                cursor = conn.cursor()
                vector_blob = vector.tobytes()
                cursor.execute("""
                    INSERT INTO comment_vectors 
                    (broadcast_id, comment_id, user_id, comment_text, vector_data, embedding_model)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (broadcast_id, comment_id, user_id, comment_text, vector_blob, 'text-embedding-3-small'))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            print(f"重複スキップ: コメントID {comment_id}")
            return False
        except Exception as e:
            print(f"保存エラー: {str(e)}")
            return False
    
    def get_status(self):
        """ベクトル化状況を確認"""
        status = {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM comments WHERE is_special_user = 1")
            status['total_special_comments'] = cursor.fetchone()[0]
        
        try:
            with sqlite3.connect(self.vector_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM comment_vectors")
                status['vectorized_comments'] = cursor.fetchone()[0]
        except:
            status['vectorized_comments'] = 0
        
        status['remaining'] = status['total_special_comments'] - status['vectorized_comments']
        
        return status

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='既存データをベクトル化')
    parser.add_argument('--limit', type=int, default=None, help='ベクトル化する件数制限')
    parser.add_argument('--status', action='store_true', help='ベクトル化状況を確認')
    
    args = parser.parse_args()
    
    vectorizer = VectorizationManager()
    
    if args.status:
        status = vectorizer.get_status()
        print("ベクトル化状況:")
        for key, value in status.items():
            print(f"  {key}: {value}")
    else:
        print("スペシャルユーザーコメントのベクトル化開始")
        vectors_saved = vectorizer.vectorize_all_special_users(limit=args.limit)
        print(f"ベクトル化完了: {vectors_saved}件")