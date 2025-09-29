#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投入済みデータをベクトル化するスクリプト
"""

import sqlite3
import numpy as np
import os
import time
import openai
import json

class VectorizationManager:
    def __init__(self, main_db_path="data/ncv_monitor.db", vector_db_path="data/vectors.db"):
        self.main_db_path = main_db_path
        self.vector_db_path = vector_db_path
        
        # 先にベクトルDBを初期化
        self.init_vector_db()
        
        # その後でAPIキーをロード
        self.api_key = self._load_api_key()
    
    def _load_api_key(self):
        """設定ファイルからAPIキーを読み込み"""
        config_path = os.path.join(os.path.dirname(__file__), "config", "ncv_special_config.json")
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            api_key = config.get('api_settings', {}).get('openai_api_key', '')
            if api_key:
                return api_key
        
        # 環境変数から取得
        return os.getenv('OPENAI_API_KEY')
    
    def init_vector_db(self):
        """ベクトルDBを初期化"""
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
                
                CREATE INDEX IF NOT EXISTS idx_comment_vectors_broadcast 
                    ON comment_vectors(broadcast_id);
                CREATE INDEX IF NOT EXISTS idx_analysis_vectors_broadcast 
                    ON analysis_vectors(broadcast_id);
            ''')
        print(f"ベクトルDB初期化完了: {self.vector_db_path}")
    
    def vectorize_all_comments(self):
        """全コメントをベクトル化"""
        
        # APIキーチェック
        if not self.api_key:
            print("APIキーが設定されていないため、ベクトル化をスキップします")
            print("config/ncv_special_config.json を作成するか、環境変数 OPENAI_API_KEY を設定してください")
            return
        
        # 1. 既にベクトル化済みのコメントIDを取得
        vectorized_comment_ids = set()
        with sqlite3.connect(self.vector_db_path) as vector_conn:
            cursor = vector_conn.cursor()
            cursor.execute("SELECT comment_id FROM comment_vectors")
            vectorized_comment_ids = {row[0] for row in cursor.fetchall()}
        
        print(f"既にベクトル化済み: {len(vectorized_comment_ids)}件")
        
        # 2. メインDBから特定ユーザーのコメントのみ取得
        with sqlite3.connect(self.main_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, broadcast_id, user_id, comment_text
                FROM comments
                WHERE comment_text != ''
                AND LENGTH(comment_text) > 3
                AND user_id = '21639740'
                ORDER BY id
            """)
            
            all_comments = cursor.fetchall()
            # 未ベクトル化のコメントのみ抽出
            comments = [c for c in all_comments if c[0] not in vectorized_comment_ids]
        
        print(f"ユーザーID 21639740 のベクトル化対象コメント: {len(comments)}件")
        
        if not comments:
            print("ベクトル化対象のコメントがありません")
            return
        
        print(f"APIキー確認: {self.api_key[:10]}...{self.api_key[-4:] if len(self.api_key) > 14 else self.api_key}")
        
        vectorized_count = 0
        
        for i, (comment_id, broadcast_id, user_id, comment_text) in enumerate(comments, 1):
            print(f"処理中 {i}/{len(comments)}: {comment_text[:50]}...")
            
            # ベクトル化
            vector = self._get_embedding(comment_text)
            if vector is None:
                print(f"  スキップ: ベクトル化失敗")
                continue
            
            # ベクトルを保存
            try:
                with sqlite3.connect(self.vector_db_path) as vector_conn:
                    vector_cursor = vector_conn.cursor()
                    vector_blob = vector.tobytes()
                    
                    vector_cursor.execute("""
                        INSERT INTO comment_vectors 
                        (broadcast_id, comment_id, user_id, comment_text, vector_data, embedding_model)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (broadcast_id, comment_id, user_id, comment_text, 
                          vector_blob, 'text-embedding-3-small'))
                    
                    vectorized_count += 1
                    print(f"  保存完了: comment_id={comment_id}")
                    
            except sqlite3.IntegrityError:
                print(f"  スキップ: 重複 comment_id={comment_id}")
            except Exception as e:
                print(f"  エラー: {str(e)}")
            
            # API制限対策
            time.sleep(0.1)
            
            # 10件ごとに進捗表示
            if i % 10 == 0:
                print(f"進捗: {i}/{len(comments)} ({vectorized_count}件保存済み)")
        
        print(f"ユーザーID 21639740 のコメントベクトル化完了: {vectorized_count}件")
    
    def vectorize_all_analyses(self):
        """特定ユーザーのAI分析をベクトル化"""
        
        # APIキーチェック
        if not self.api_key:
            print("APIキーが設定されていないため、AI分析ベクトル化をスキップします")
            return
        
        # 1. 既にベクトル化済みのAI分析IDを取得
        vectorized_analysis_ids = set()
        with sqlite3.connect(self.vector_db_path) as vector_conn:
            cursor = vector_conn.cursor()
            cursor.execute("SELECT analysis_id FROM analysis_vectors")
            vectorized_analysis_ids = {row[0] for row in cursor.fetchall()}
        
        print(f"既にベクトル化済みAI分析: {len(vectorized_analysis_ids)}件")
        
        # 2. メインDBから特定ユーザーのAI分析のみ取得
        with sqlite3.connect(self.main_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, broadcast_id, user_id, analysis_result
                FROM ai_analyses
                WHERE analysis_result != ''
                AND user_id = '21639740'
                ORDER BY id
            """)
            
            all_analyses = cursor.fetchall()
            # 未ベクトル化のAI分析のみ抽出
            analyses = [a for a in all_analyses if a[0] not in vectorized_analysis_ids]
        
        print(f"ユーザーID 21639740 のベクトル化対象AI分析: {len(analyses)}件")
        
        if not analyses:
            print("ベクトル化対象のAI分析がありません")
            return
        
        vectorized_count = 0
        
        for i, (analysis_id, broadcast_id, user_id, analysis_text) in enumerate(analyses, 1):
            print(f"処理中 {i}/{len(analyses)}: AI分析ID={analysis_id}")
            
            # 長いテキストは最初の500文字のみ
            analysis_summary = analysis_text[:500]
            
            # ベクトル化
            vector = self._get_embedding(analysis_summary)
            if vector is None:
                print(f"  スキップ: ベクトル化失敗")
                continue
            
            # ベクトルを保存
            try:
                with sqlite3.connect(self.vector_db_path) as vector_conn:
                    vector_cursor = vector_conn.cursor()
                    vector_blob = vector.tobytes()
                    
                    vector_cursor.execute("""
                        INSERT INTO analysis_vectors 
                        (broadcast_id, analysis_id, user_id, analysis_text, vector_data, embedding_model)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (broadcast_id, analysis_id, user_id, analysis_summary, 
                          vector_blob, 'text-embedding-3-small'))
                    
                    vectorized_count += 1
                    print(f"  保存完了: analysis_id={analysis_id}")
                    
            except sqlite3.IntegrityError:
                print(f"  スキップ: 重複 analysis_id={analysis_id}")
            except Exception as e:
                print(f"  エラー: {str(e)}")
            
            # API制限対策
            time.sleep(0.1)
        
        print(f"ユーザーID 21639740 のAI分析ベクトル化完了: {vectorized_count}件")
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """テキストをベクトル化"""
        try:
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            return np.array(response.data[0].embedding, dtype=np.float32)
            
        except Exception as e:
            print(f"ベクトル化エラー: {str(e)}")
            return None
    
    def show_status(self):
        """現在の状況を表示"""
        
        # メインDBの状況
        with sqlite3.connect(self.main_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM comments WHERE comment_text != '' AND LENGTH(comment_text) > 3")
            total_comments = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ai_analyses WHERE analysis_result != ''")
            total_analyses = cursor.fetchone()[0]
        
        # ベクトルDBの状況
        vectorized_comments = 0
        vectorized_analyses = 0
        if os.path.exists(self.vector_db_path):
            with sqlite3.connect(self.vector_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM comment_vectors")
                vectorized_comments = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM analysis_vectors")
                vectorized_analyses = cursor.fetchone()[0]
        
        print("=== ベクトル化状況 ===")
        print(f"コメント: {vectorized_comments}/{total_comments} ベクトル化済み")
        print(f"AI分析: {vectorized_analyses}/{total_analyses} ベクトル化済み")
        print(f"未処理コメント: {total_comments - vectorized_comments}件")
        print(f"未処理AI分析: {total_analyses - vectorized_analyses}件")

def main():
    vectorizer = VectorizationManager()
    
    print("現在の状況:")
    vectorizer.show_status()
    
    if not vectorizer.api_key:
        print("\nAPIキーが設定されていないため、ベクトル化をスキップします")
        print("config/ncv_special_config.json を作成してから再実行してください")
        return
    
    print("\nベクトル化を開始します...")
    
    # コメントをベクトル化
    vectorizer.vectorize_all_comments()
    
    # AI分析をベクトル化
    vectorizer.vectorize_all_analyses()
    
    print("\n最終状況:")
    vectorizer.show_status()
    
    print("\nベクトル化完了! RAGシステムが使用可能になりました。")

if __name__ == "__main__":
    main()