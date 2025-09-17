# rag/rag_core.py（完成形）
import sqlite3
import numpy as np
import os
from typing import List, Dict, Optional
from .statistical import StatisticalAnalyzer

class RAGSystem:
    """RAGシステムのメインクラス"""
    
    def __init__(self, main_db_path="data/ncv_monitor.db", vector_db_path="data/vectors.db"):
        self.main_db_path = main_db_path
        self.vector_db_path = vector_db_path
        
        # 統計分析機能
        self.statistical_analyzer = StatisticalAnalyzer(main_db_path)
        
        # DBの存在チェック
        if not os.path.exists(self.vector_db_path):
            print(f"⚠️ ベクトルDBが見つかりません: {self.vector_db_path}")
        
        if not os.path.exists(self.main_db_path):
            print(f"⚠️ メインDBが見つかりません: {self.main_db_path}")
    
    def query(self, question: str, user_id: Optional[str] = None, 
              broadcast_id: Optional[int] = None, top_k: int = 5) -> Dict:
        """メインクエリ処理"""
        
        print(f"🔍 RAG Query: '{question}'")
        if user_id:
            print(f"   ユーザーフィルター: {user_id}")
        if broadcast_id:
            print(f"   放送フィルター: {broadcast_id}")
        
        # 質問の種類を判定
        query_type = self._classify_question(question)
        print(f"   クエリタイプ: {query_type}")
        
        if query_type == "statistical":
            return self._handle_statistical_query(question, user_id, broadcast_id)
        else:
            return self._handle_semantic_query(question, user_id, broadcast_id, top_k)
    
    def _classify_question(self, question: str) -> str:
        """質問の種類を分類"""
        statistical_keywords = [
            "よく", "頻繁", "多く", "ランキング", "順位", "回数", "統計", 
            "傾向", "パターン", "分析", "どのくらい", "何回", "どの配信者",
            "何人", "誰が", "どこの", "いつ", "時間帯", "月", "日"
        ]
        
        question_lower = question.lower()
        for keyword in statistical_keywords:
            if keyword in question_lower:
                return "statistical"
        
        return "semantic"
    
    def _handle_statistical_query(self, question: str, user_id: Optional[str], 
                                 broadcast_id: Optional[int]) -> Dict:
        """統計的質問への対応"""
        print("📊 統計分析モードで処理中...")
        return self.statistical_analyzer.analyze(question, user_id, broadcast_id)
    
    def _handle_semantic_query(self, question: str, user_id: Optional[str], 
                              broadcast_id: Optional[int], top_k: int) -> Dict:
        """セマンティック検索（類似度ベース）"""
        
        print("🔍 セマンティック検索モードで処理中...")
        
        # 1. 質問をベクトル化
        question_vector = self._get_embedding(question)
        if question_vector is None:
            return {
                'answer': "❌ 質問のベクトル化に失敗しました。OpenAI APIキーを確認してください。",
                'sources': [],
                'query_type': 'semantic',
                'error': 'embedding_failed'
            }
        
        # 2. 類似検索
        similar_comments = self._search_similar_comments(question_vector, top_k, user_id, broadcast_id)
        similar_analyses = self._search_similar_analyses(question_vector, top_k, user_id, broadcast_id)
        
        print(f"   検索結果: コメント{len(similar_comments)}件, AI分析{len(similar_analyses)}件")
        
        # 3. コンテキスト構築
        context = self._build_context(similar_comments, similar_analyses)
        
        if not context.strip():
            return {
                'answer': "🤷 指定された条件で関連する情報が見つかりませんでした。",
                'sources': [],
                'query_type': 'semantic',
                'filters_applied': {'user_id': user_id, 'broadcast_id': broadcast_id}
            }
        
        # 4. 回答生成
        answer = self._generate_answer(question, context, user_id, broadcast_id)
        sources = self._format_sources(similar_comments, similar_analyses)
        
        return {
            'answer': answer,
            'sources': sources,
            'query_type': 'semantic',
            'total_sources': len(sources),
            'filters_applied': {'user_id': user_id, 'broadcast_id': broadcast_id}
        }
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """テキストをベクトル化"""
        try:
            import openai
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print("❌ OpenAI APIキーが設定されていません（環境変数 OPENAI_API_KEY）")
                return None
            
            client = openai.OpenAI(api_key=api_key)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            vector = np.array(response.data[0].embedding, dtype=np.float32)
            print(f"   ✅ ベクトル化完了: {len(vector)}次元")
            return vector
            
        except ImportError:
            print("❌ openaiライブラリがインストールされていません: pip install openai")
            return None
        except Exception as e:
            print(f"❌ ベクトル化エラー: {str(e)}")
            return None
    
    def _search_similar_comments(self, query_vector: np.ndarray, top_k: int,
                                user_id: Optional[str] = None, 
                                broadcast_id: Optional[int] = None) -> List[Dict]:
        """類似コメント検索"""
        try:
            if not os.path.exists(self.vector_db_path):
                print("❌ ベクトルDBが存在しません")
                return []
            
            with sqlite3.connect(self.vector_db_path) as conn:
                cursor = conn.cursor()
                
                # フィルター条件を動的に構築
                query = """
                    SELECT cv.comment_id, cv.user_id, cv.comment_text, cv.vector_data, cv.broadcast_id
                    FROM comment_vectors cv
                    WHERE 1=1
                """
                params = []
                
                if user_id:
                    query += " AND cv.user_id = ?"
                    params.append(user_id)
                
                if broadcast_id:
                    query += " AND cv.broadcast_id = ?"
                    params.append(broadcast_id)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                if not rows:
                    print("   ベクトル化されたコメントが見つかりません")
                    return []
                
                print(f"   検索対象ベクトル: {len(rows)}件")
                
                results = []
                for row in rows:
                    comment_id, uid, comment_text, vector_blob, bid = row
                    
                    try:
                        stored_vector = np.frombuffer(vector_blob, dtype=np.float32)
                        similarity = self._cosine_similarity(query_vector, stored_vector)
                        
                        results.append({
                            'comment_id': comment_id,
                            'user_id': uid,
                            'comment_text': comment_text,
                            'broadcast_id': bid,
                            'similarity': similarity,
                            'type': 'comment'
                        })
                    except Exception as e:
                        print(f"   ベクトル復元エラー（コメントID: {comment_id}）: {str(e)}")
                        continue
            
            # 類似度順にソート
            results.sort(key=lambda x: x['similarity'], reverse=True)
            top_results = results[:top_k]
            
            # 追加情報を取得
            enriched_results = self._enrich_comment_results(top_results)
            
            print(f"   類似コメント: {len(enriched_results)}件（最高類似度: {top_results[0]['similarity']:.3f if top_results else 0}）")
            return enriched_results
            
        except Exception as e:
            print(f"❌ コメント検索エラー: {str(e)}")
            return []
    
    def _search_similar_analyses(self, query_vector: np.ndarray, top_k: int,
                                user_id: Optional[str] = None,
                                broadcast_id: Optional[int] = None) -> List[Dict]:
        """類似AI分析検索"""
        try:
            if not os.path.exists(self.vector_db_path):
                return []
            
            with sqlite3.connect(self.vector_db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT av.analysis_id, av.user_id, av.analysis_text, av.vector_data, av.broadcast_id
                    FROM analysis_vectors av
                    WHERE 1=1
                """
                params = []
                
                if user_id:
                    query += " AND av.user_id = ?"
                    params.append(user_id)
                
                if broadcast_id:
                    query += " AND av.broadcast_id = ?"
                    params.append(broadcast_id)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                if not rows:
                    print("   ベクトル化されたAI分析が見つかりません")
                    return []
                
                print(f"   検索対象AI分析: {len(rows)}件")
                
                results = []
                for row in rows:
                    analysis_id, uid, analysis_text, vector_blob, bid = row
                    
                    try:
                        stored_vector = np.frombuffer(vector_blob, dtype=np.float32)
                        similarity = self._cosine_similarity(query_vector, stored_vector)
                        
                        results.append({
                            'analysis_id': analysis_id,
                            'user_id': uid,
                            'analysis_text': analysis_text,
                            'broadcast_id': bid,
                            'similarity': similarity,
                            'type': 'analysis'
                        })
                    except Exception as e:
                        print(f"   ベクトル復元エラー（AI分析ID: {analysis_id}）: {str(e)}")
                        continue
            
            results.sort(key=lambda x: x['similarity'], reverse=True)
            top_results = results[:top_k]
            
            enriched_results = self._enrich_analysis_results(top_results)
            
            print(f"   類似AI分析: {len(enriched_results)}件")
            return enriched_results
            
        except Exception as e:
            print(f"❌ AI分析検索エラー: {str(e)}")
            return []
    
    def _enrich_comment_results(self, results: List[Dict]) -> List[Dict]:
        """コメント検索結果に追加情報を付与"""
        if not results:
            return results
        
        try:
            comment_ids = [r['comment_id'] for r in results]
            placeholders = ','.join(['?' for _ in comment_ids])
            
            with sqlite3.connect(self.main_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT c.id, c.user_name, c.timestamp, c.elapsed_time,
                           b.lv_value, b.live_title, b.start_time,
                           su.display_name
                    FROM comments c
                    JOIN broadcasts b ON c.broadcast_id = b.id
                    LEFT JOIN special_users su ON c.user_id = su.user_id
                    WHERE c.id IN ({placeholders})
                """, comment_ids)
                
                enrichment_data = {}
                for row in cursor.fetchall():
                    comment_id, user_name, timestamp, elapsed_time, lv_value, live_title, start_time, display_name = row
                    enrichment_data[comment_id] = {
                        'user_name': user_name,
                        'display_name': display_name or user_name,
                        'timestamp': timestamp,
                        'elapsed_time': elapsed_time,
                        'lv_value': lv_value,
                        'live_title': live_title,
                        'start_time': start_time
                    }
            
            # 結果に追加情報をマージ
            for result in results:
                comment_id = result['comment_id']
                if comment_id in enrichment_data:
                    result.update(enrichment_data[comment_id])
            
            return results
            
        except Exception as e:
            print(f"❌ コメント情報取得エラー: {str(e)}")
            return results
    
    def _enrich_analysis_results(self, results: List[Dict]) -> List[Dict]:
        """AI分析検索結果に追加情報を付与"""
        if not results:
            return results
        
        try:
            analysis_ids = [r['analysis_id'] for r in results]
            placeholders = ','.join(['?' for _ in analysis_ids])
            
            with sqlite3.connect(self.main_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT a.id, a.model_used, a.comment_count, a.analysis_date,
                           b.lv_value, b.live_title, b.start_time,
                           su.display_name
                    FROM ai_analyses a
                    JOIN broadcasts b ON a.broadcast_id = b.id
                    LEFT JOIN special_users su ON a.user_id = su.user_id
                    WHERE a.id IN ({placeholders})
                """, analysis_ids)
                
                enrichment_data = {}
                for row in cursor.fetchall():
                    analysis_id, model_used, comment_count, analysis_date, lv_value, live_title, start_time, display_name = row
                    enrichment_data[analysis_id] = {
                        'model_used': model_used,
                        'comment_count': comment_count,
                        'analysis_date': analysis_date,
                        'lv_value': lv_value,
                        'live_title': live_title,
                        'start_time': start_time,
                        'display_name': display_name
                    }
            
            for result in results:
                analysis_id = result['analysis_id']
                if analysis_id in enrichment_data:
                    result.update(enrichment_data[analysis_id])
            
            return results
            
        except Exception as e:
            print(f"❌ AI分析情報取得エラー: {str(e)}")
            return results
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """コサイン類似度計算"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm_a = np.linalg.norm(vec1)
            norm_b = np.linalg.norm(vec2)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
                
            return float(dot_product / (norm_a * norm_b))
            
        except Exception as e:
            print(f"❌ 類似度計算エラー: {str(e)}")
            return 0.0
    
    def _build_context(self, comments: List[Dict], analyses: List[Dict]) -> str:
        """検索結果からコンテキストを構築"""
        context_parts = []
        
        # コメント情報を追加
        if comments:
            context_parts.append("【関連するコメント】")
            for i, comment in enumerate(comments, 1):
                user_name = comment.get('display_name', comment.get('user_name', '不明'))
                live_title = comment.get('live_title', '不明な配信')
                elapsed_time = comment.get('elapsed_time', '不明')
                similarity = comment.get('similarity', 0)
                
                context_parts.append(
                    f"{i}. {user_name}: 「{comment['comment_text']}」"
                    f"\n   配信: {live_title} ({elapsed_time}) [類似度: {similarity:.3f}]"
                )
        
        # AI分析情報を追加
        if analyses:
            context_parts.append("\n【関連するAI分析】")
            for i, analysis in enumerate(analyses, 1):
                user_name = analysis.get('display_name', f"ユーザー{analysis['user_id']}")
                live_title = analysis.get('live_title', '不明な配信')
                model_used = analysis.get('model_used', '不明')
                similarity = analysis.get('similarity', 0)
                
                # 分析結果は長いので要約
                analysis_preview = analysis['analysis_text'][:200] + "..."
                
                context_parts.append(
                    f"{i}. {user_name}の分析 (by {model_used}): {analysis_preview}"
                    f"\n   配信: {live_title} [類似度: {similarity:.3f}]"
                )
        
        return "\n\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str, 
                        user_id: Optional[str], broadcast_id: Optional[int]) -> str:
        """LLMで回答生成"""
        try:
            import openai
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return "❌ OpenAI APIキーが設定されていません（環境変数 OPENAI_API_KEY）"
            
            client = openai.OpenAI(api_key=api_key)
            
            # フィルター情報を含むシステムプロンプト
            filter_info = []
            if user_id:
                filter_info.append(f"特定ユーザー: {user_id}")
            if broadcast_id:
                filter_info.append(f"特定放送: {broadcast_id}")
            
            filter_text = f"（検索条件: {', '.join(filter_info)}）" if filter_info else ""
            
            system_prompt = f"""あなたはニコニコ生放送の分析専門家です。
配信のコメントやAI分析結果を基に、ユーザーの質問に答えてください。

{filter_text}

回答の際は以下を心がけてください：
- 提供された情報を具体的に引用する
- 推測と事実を明確に区別する
- 情報が不足している場合はその旨を述べる
- 検索条件が適用されている場合はその範囲内での回答であることを明記する
- 簡潔で分かりやすい日本語で回答する"""

            user_prompt = f"""
質問: {question}

参考情報:
{context}

上記の情報を基に、質問に対する詳細で有用な回答を提供してください。
"""
            
            print("🤖 AI回答生成中...")
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            print("✅ AI回答生成完了")
            
            return answer
            
        except ImportError:
            return "❌ openaiライブラリがインストールされていません: pip install openai"
        except Exception as e:
            print(f"❌ 回答生成エラー: {str(e)}")
            return f"回答生成中にエラーが発生しました: {str(e)}"
    
    def _format_sources(self, comments: List[Dict], analyses: List[Dict]) -> List[Dict]:
        """ソース情報を整形"""
        sources = []
        
        for comment in comments:
            sources.append({
                'type': 'comment',
                'content': comment['comment_text'],
                'user_name': comment.get('display_name', comment.get('user_name', '不明')),
                'user_id': comment['user_id'],
                'live_title': comment.get('live_title', '不明'),
                'lv_value': comment.get('lv_value', '不明'),
                'elapsed_time': comment.get('elapsed_time', '不明'),
                'similarity': comment.get('similarity', 0)
            })
        
        for analysis in analyses:
            sources.append({
                'type': 'analysis',
                'content': analysis['analysis_text'][:200] + "...",
                'user_name': analysis.get('display_name', f"ユーザー{analysis['user_id']}"),
                'user_id': analysis['user_id'],
                'live_title': analysis.get('live_title', '不明'),
                'lv_value': analysis.get('lv_value', '不明'),
                'model_used': analysis.get('model_used', '不明'),
                'similarity': analysis.get('similarity', 0)
            })
        
        return sources
    
    def get_status(self) -> Dict:
        """システム状況取得"""
        status = {
            'vector_db_exists': os.path.exists(self.vector_db_path),
            'main_db_exists': os.path.exists(self.main_db_path),
            'total_comment_vectors': 0,
            'total_analysis_vectors': 0,
            'unique_broadcasts': 0,
            'unique_users': 0
        }
        
        if status['vector_db_exists']:
            try:
                with sqlite3.connect(self.vector_db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT COUNT(*) FROM comment_vectors")
                    status['total_comment_vectors'] = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM analysis_vectors")
                    status['total_analysis_vectors'] = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(DISTINCT broadcast_id) FROM comment_vectors")
                    status['unique_broadcasts'] = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM comment_vectors")
                    status['unique_users'] = cursor.fetchone()[0]
            except Exception as e:
                print(f"❌ ステータス取得エラー: {str(e)}")
        
        return status
    
    def search_by_user(self, user_id: str, limit: int = 10) -> Dict:
        """特定ユーザーの情報を検索"""
        return self.query(f"ユーザー{user_id}の情報", user_id=user_id, top_k=limit)
    
    def search_by_broadcast(self, broadcast_id: int, limit: int = 10) -> Dict:
        """特定放送の情報を検索"""
        return self.query("この放送の情報", broadcast_id=broadcast_id, top_k=limit)