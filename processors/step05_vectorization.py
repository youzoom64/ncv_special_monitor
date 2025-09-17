# processors/step05_vectorization.py
import sqlite3
import numpy as np
import os
import time
from typing import List, Dict

def process(pipeline_data):
    """Step05: ベクトル化処理（新規データのみ）"""
    try:
        # Step04のDB保存結果を取得
        step04_results = pipeline_data['results']['step04_database_storage']
        broadcast_id = step04_results['broadcast_id']
        
        print(f"Step05 開始: ベクトル化処理 - broadcast_id={broadcast_id}")
        
        # 設定チェック
        config = pipeline_data['config']
        vectorization_enabled = config.get('vectorization_settings', {}).get('enabled', False)
        
        if not vectorization_enabled:
            print("ベクトル化が無効です（設定で有効化してください）")
            return {
                "vectorization_completed": False, 
                "reason": "disabled_in_config"
            }
        
        # ベクトル化実行
        vectorizer = VectorizationManager()
        vectors_saved = vectorizer.vectorize_broadcast_incremental(broadcast_id)
        
        print(f"Step05 完了: {vectors_saved}個のベクトルを保存")
        
        return {
            "vectorization_completed": True,
            "vectors_saved": vectors_saved,
            "broadcast_id": broadcast_id
        }
        
    except Exception as e:
        print(f"Step05 エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "vectorization_completed": False,
            "error": str(e)
        }

class VectorizationManager:
    def __init__(self):
        self.db_path = "data/ncv_monitor.db"
        self.vector_db_path = "data/vectors.db"
        self.init_vector_db()
    
    def init_vector_db(self):
        """ベクトルデータベース初期化"""
        os.makedirs(os.path.dirname(self.vector_db_path), exist_ok=True)
        
        with sqlite3.connect(self.vector_db_path) as conn:
            conn.executescript('''
                -- コメントベクトルテーブル
                CREATE TABLE IF NOT EXISTS comment_vectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broadcast_id INTEGER,
                    comment_id INTEGER UNIQUE,  -- 重複防止
                    user_id TEXT,
                    comment_text TEXT,
                    vector_data BLOB,  -- numpy配列をバイナリ保存
                    embedding_model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- AI分析ベクトルテーブル
                CREATE TABLE IF NOT EXISTS analysis_vectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broadcast_id INTEGER,
                    analysis_id INTEGER UNIQUE,  -- 重複防止
                    user_id TEXT,
                    analysis_text TEXT,
                    vector_data BLOB,
                    embedding_model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- インデックス
                CREATE INDEX IF NOT EXISTS idx_comment_vectors_broadcast 
                    ON comment_vectors(broadcast_id);
                CREATE INDEX IF NOT EXISTS idx_analysis_vectors_broadcast 
                    ON analysis_vectors(broadcast_id);
            ''')
        print(f"ベクトルDB初期化完了: {self.vector_db_path}")
    
    def vectorize_broadcast_incremental(self, broadcast_id: int) -> int:
        """指定放送の新規データのみベクトル化"""
        
        print(f"=== 放送 {broadcast_id} の増分ベクトル化開始 ===")
        
        # 1. 新規コメントをベクトル化
        new_comment_vectors = self._vectorize_new_comments(broadcast_id)
        
        # 2. 新規AI分析をベクトル化  
        new_analysis_vectors = self._vectorize_new_analyses(broadcast_id)
        
        # 3. ベクトルを保存
        total_saved = 0
        if new_comment_vectors or new_analysis_vectors:
            total_saved = self._save_vectors(broadcast_id, new_comment_vectors, new_analysis_vectors)
        else:
            print("新規ベクトルなし")
        
        print(f"=== 処理完了: {total_saved}件保存 ===")
        return total_saved
    
    def _vectorize_new_comments(self, broadcast_id: int) -> List[Dict]:
        """新規コメントのみベクトル化"""
        
        # 未処理のコメントを取得（LEFT JOINで既存ベクトルと突き合わせ）
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, c.user_id, c.comment_text, c.user_name
                FROM comments c
                LEFT JOIN comment_vectors cv ON c.id = cv.comment_id
                WHERE c.broadcast_id = ?
                AND c.is_special_user = 1  -- 特別ユーザーのみ
                AND c.comment_text != ''
                AND LENGTH(c.comment_text) > 3
                AND cv.comment_id IS NULL  -- まだベクトル化されていない
                ORDER BY c.timestamp
            """, (broadcast_id,))
            
            new_comments = cursor.fetchall()
        
        print(f"新規コメント: {len(new_comments)}件")
        
        vectors = []
        for comment_id, user_id, comment_text, user_name in new_comments:
            print(f"  処理中: ID {comment_id} - {comment_text[:30]}...")
            
            vector = self._get_embedding(comment_text)
            if vector is not None:
                vectors.append({
                    'comment_id': comment_id,
                    'user_id': user_id,
                    'text': comment_text,
                    'vector': vector
                })
            
            time.sleep(0.1)  # API制限対策
        
        return vectors
    
    def _vectorize_new_analyses(self, broadcast_id: int) -> List[Dict]:
        """新規AI分析のみベクトル化"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id, a.user_id, a.analysis_result
                FROM ai_analyses a
                LEFT JOIN analysis_vectors av ON a.id = av.analysis_id
                WHERE a.broadcast_id = ?
                AND a.analysis_result != ''
                AND av.analysis_id IS NULL  -- まだベクトル化されていない
                ORDER BY a.analysis_date
            """, (broadcast_id,))
            
            new_analyses = cursor.fetchall()
        
        print(f"新規AI分析: {len(new_analyses)}件")
        
        vectors = []
        for analysis_id, user_id, analysis_text in new_analyses:
            print(f"  処理中: AI分析ID {analysis_id}")
            
            # AI分析は長いので最初の500文字のみベクトル化
            analysis_summary = analysis_text[:500]
            vector = self._get_embedding(analysis_summary)
            
            if vector is not None:
                vectors.append({
                    'analysis_id': analysis_id,
                    'user_id': user_id,
                    'text': analysis_summary,
                    'vector': vector
                })
            
            time.sleep(0.1)
        
        return vectors
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """テキストをベクトル化（OpenAI Embeddings使用）"""
        try:
            import openai
            
            # OpenAI APIキーを取得
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print("OpenAI APIキーが設定されていません（環境変数 OPENAI_API_KEY）")
                return None
            
            client = openai.OpenAI(api_key=api_key)
            
            response = client.embeddings.create(
                model="text-embedding-3-small",  # 安価なモデル
                input=text
            )
            
            return np.array(response.data[0].embedding, dtype=np.float32)
            
        except Exception as e:
            print(f"ベクトル化エラー: {str(e)}")
            return None
    
    def _save_vectors(self, broadcast_id: int, comment_vectors: List[Dict], 
                     analysis_vectors: List[Dict]) -> int:
        """ベクトルをDBに保存"""
        
        with sqlite3.connect(self.vector_db_path) as conn:
            cursor = conn.cursor()
            saved_count = 0
            
            # コメントベクトル保存
            for cv in comment_vectors:
                try:
                    vector_blob = cv['vector'].tobytes()
                    cursor.execute("""
                        INSERT INTO comment_vectors 
                        (broadcast_id, comment_id, user_id, comment_text, vector_data, embedding_model)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (broadcast_id, cv['comment_id'], cv['user_id'], 
                          cv['text'], vector_blob, 'text-embedding-3-small'))
                    saved_count += 1
                except sqlite3.IntegrityError:
                    print(f"重複スキップ: コメントID {cv['comment_id']}")
            
            # AI分析ベクトル保存
            for av in analysis_vectors:
                try:
                    vector_blob = av['vector'].tobytes()
                    cursor.execute("""
                        INSERT INTO analysis_vectors 
                        (broadcast_id, analysis_id, user_id, analysis_text, vector_data, embedding_model)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (broadcast_id, av['analysis_id'], av['user_id'], 
                          av['text'], vector_blob, 'text-embedding-3-small'))
                    saved_count += 1
                except sqlite3.IntegrityError:
                    print(f"重複スキップ: AI分析ID {av['analysis_id']}")
        
        return saved_count