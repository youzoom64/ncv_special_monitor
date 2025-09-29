# rag_system.py
import sqlite3
import numpy as np
import os
from typing import List, Dict, Tuple
import openai
import json

class RAGSearchSystem:
    def __init__(self, main_db_path="data/ncv_monitor.db", vector_db_path="data/vectors.db"):
        self.main_db_path = main_db_path
        self.vector_db_path = vector_db_path
        
        # DBの存在チェック
        if not os.path.exists(self.vector_db_path):
            print(f"⚠️ ベクトルDBが見つかりません: {self.vector_db_path}")
            print("先にベクトル化を実行してください")
    
    def classify_question_with_llm(self, question: str) -> Dict:
        """
        LLMで質問意図と検索深度を分類
        例: {"category": "comment_search", "search_depth": "high"}
        """
        config_path = os.path.join(os.path.dirname(__file__), "config", "ncv_special_config.json")
        api_key = None
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            api_key = config.get('api_settings', {}).get('openai_api_key', '')

        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            print("❌ OpenAI APIキーが設定されていません（分類スキップ）")
            return {"category": "comment_search", "search_depth": "medium"}  # デフォルト

        client = openai.OpenAI(api_key=api_key, timeout=10.0)

        system_prompt = """あなたはRAG検索の質問分類エージェントです。
    目的は、ユーザー質問を解析し、コメントDBや配信DBから検索する必要があるか判断することです。

    分類は次の通り:
    1. category:
    - comment_search: 面白いコメントや盛り上がったコメントを探す質問
    - user_search: 特定ユーザーや名前についての質問（例: この人どんな発言してる？）
    - broadcast_info: 配信や放送内容について（例: この枠で何があった？）
    - general: DB検索不要、LLMのみで答えられる

    2. search_depth:
    - low: 少量の結果で十分
    - medium: 通常量
    - high: できるだけ多くの結果が必要

    出力は必ずJSONのみで:
    {"category": "comment_search", "search_depth": "medium"}"""

        user_prompt = f"質問: {question}"

        print(f"🧭 質問分類中 (miniモデル使用): {question}")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=50,
            temperature=0
        )

        try:
            result = json.loads(response.choices[0].message.content.strip())
        except Exception:
            result = {"category": "comment_search", "search_depth": "medium"}

        print(f"🧭 LLM分類結果: {result}")
        return result


    def search_and_answer(self, question: str, top_k: int = 5, user_id: str = None) -> str:
        """質問に対してRAG検索して回答生成"""
        print(f"🔍 RAG検索開始: '{question}'")

        # 1. 質問意図を分類（LLM or rule-based）
        classification = self.classify_question_with_llm(question)
        category = classification["category"]
        depth = classification["search_depth"]
        top_k = {"low": 3, "medium": 5, "high": 10}.get(depth, 5)

        if category == "general":
            print("🧭 カテゴリ: general → ベクトル検索スキップ")
            return self._generate_answer(question, "")

        # 2. 質問をベクトル化
        question_vector = self._get_embedding(question)
        if question_vector is None:
            return "❌ 質問のベクトル化に失敗しました"

        # 3. 類似コンテンツを検索
        similar_comments = self._search_similar_comments(question_vector, top_k)
        if user_id:
            before_count = len(similar_comments)
            similar_comments = [c for c in similar_comments if str(c['user_id']) == str(user_id)]
            print(f"🧭 user_idフィルタ適用: {before_count} → {len(similar_comments)} 件")

        similar_analyses = self._search_similar_analyses(question_vector, top_k)

        print(f"📊 検索結果: コメント{len(similar_comments)}件, AI分析{len(similar_analyses)}件")

        # 4. コンテキスト構築
        context = self._build_context(similar_comments, similar_analyses)

        if not context.strip():
            return "🤷 関連する情報が見つかりませんでした"

        # 5. LLMで回答生成
        answer = self._generate_answer(question, context)
        return answer

        
    def _get_embedding(self, text: str) -> np.ndarray:
        """テキストをベクトル化"""
        try:
            import openai
            import json
            
            # 設定ファイルからAPIキーを取得
            config_path = os.path.join(os.path.dirname(__file__), "config", "ncv_special_config.json")

            api_key = None
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                api_key = config.get('api_settings', {}).get('openai_api_key', '')
            
            if not api_key:
                api_key = os.getenv('OPENAI_API_KEY')
                
            if not api_key:
                print("❌ OpenAI APIキーが設定されていません")
                return None
            
            client = openai.OpenAI(api_key=api_key)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            return np.array(response.data[0].embedding, dtype=np.float32)
            
        except Exception as e:
            print(f"❌ ベクトル化エラー: {str(e)}")
            return None
    
    def _search_similar_comments(self, query_vector: np.ndarray, top_k: int) -> List[Dict]:
        """類似コメントを検索"""
        
        try:
            with sqlite3.connect(self.vector_db_path) as vector_conn:
                cursor = vector_conn.cursor()
                cursor.execute("""
                    SELECT cv.comment_id, cv.user_id, cv.comment_text, cv.vector_data, cv.broadcast_id
                    FROM comment_vectors cv
                """)
                
                results = []
                for row in cursor.fetchall():
                    comment_id, user_id, comment_text, vector_blob, broadcast_id = row
                    
                    # ベクトル復元
                    stored_vector = np.frombuffer(vector_blob, dtype=np.float32)
                    
                    # コサイン類似度計算
                    similarity = self._cosine_similarity(query_vector, stored_vector)
                    
                    results.append({
                        'comment_id': comment_id,
                        'user_id': user_id,
                        'comment_text': comment_text,
                        'broadcast_id': broadcast_id,
                        'similarity': similarity,
                        'type': 'comment'
                    })
            
            # 類似度順にソート
            results.sort(key=lambda x: x['similarity'], reverse=True)
            top_results = results[:top_k]
            
            # 追加情報を取得（ユーザー名、放送タイトルなど）
            enriched_results = self._enrich_comment_results(top_results)
            
            print(f"💬 類似コメント検索完了: {len(enriched_results)}件")
            return enriched_results
            
        except Exception as e:
            print(f"❌ コメント検索エラー: {str(e)}")
            return []
    
    def _search_similar_analyses(self, query_vector: np.ndarray, top_k: int) -> List[Dict]:
        """類似AI分析を検索"""
        
        try:
            with sqlite3.connect(self.vector_db_path) as vector_conn:
                cursor = vector_conn.cursor()
                cursor.execute("""
                    SELECT av.analysis_id, av.user_id, av.analysis_text, av.vector_data, av.broadcast_id
                    FROM analysis_vectors av
                """)
                
                results = []
                for row in cursor.fetchall():
                    analysis_id, user_id, analysis_text, vector_blob, broadcast_id = row
                    
                    # ベクトル復元
                    stored_vector = np.frombuffer(vector_blob, dtype=np.float32)
                    
                    # コサイン類似度計算
                    similarity = self._cosine_similarity(query_vector, stored_vector)
                    
                    results.append({
                        'analysis_id': analysis_id,
                        'user_id': user_id,
                        'analysis_text': analysis_text,
                        'broadcast_id': broadcast_id,
                        'similarity': similarity,
                        'type': 'analysis'
                    })
            
            # 類似度順にソート
            results.sort(key=lambda x: x['similarity'], reverse=True)
            top_results = results[:top_k]
            
            # 追加情報を取得
            enriched_results = self._enrich_analysis_results(top_results)
            
            print(f"🤖 類似AI分析検索完了: {len(enriched_results)}件")
            return enriched_results
            
        except Exception as e:
            print(f"❌ AI分析検索エラー: {str(e)}")
            return []
    
    def _enrich_comment_results(self, results: List[Dict]) -> List[Dict]:
        """コメント検索結果に追加情報を付与"""
        
        if not results:
            return results
        
        # comment_idのリストを作成
        comment_ids = [r['comment_id'] for r in results]
        placeholders = ','.join(['?' for _ in comment_ids])
        
        with sqlite3.connect(self.main_db_path) as main_conn:
            cursor = main_conn.cursor()
            cursor.execute(f"""
                SELECT c.id, c.user_name, c.timestamp, c.elapsed_time,
                       b.lv_value, b.live_title, b.start_time,
                       su.display_name
                FROM comments c
                JOIN broadcasts b ON c.broadcast_id = b.id
                LEFT JOIN special_users su ON c.user_id = su.user_id
                WHERE c.id IN ({placeholders})
            """, comment_ids)
            
            # comment_id をキーとした辞書を作成
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
                print(f"🧪 comment_id={comment_id}, display_name={result.get('display_name')}, user_name={result.get('user_name')}")

        
        return results
    
    def _enrich_analysis_results(self, results: List[Dict]) -> List[Dict]:
        """AI分析検索結果に追加情報を付与"""
        
        if not results:
            return results
        
        analysis_ids = [r['analysis_id'] for r in results]
        placeholders = ','.join(['?' for _ in analysis_ids])
        
        with sqlite3.connect(self.main_db_path) as main_conn:
            cursor = main_conn.cursor()
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
                display_name_raw = comment.get('display_name') or ''
                display_name = display_name_raw.strip()
                user_name = (comment.get('user_name') or '不明').strip()

                # ✅ 「ユーザー123456」なら user_name を優先
                if display_name.startswith("ユーザー") and display_name.replace("ユーザー", "").isdigit():
                    final_name = user_name
                else:
                    final_name = display_name or user_name

                # デバッグ出力
                print(f"🧪 context用: user_id={comment.get('user_id')}, raw_display={display_name_raw}, 採用={final_name}")

                user_id = comment.get('user_id', '不明')
                live_title = comment.get('live_title', '不明な配信')
                elapsed_time = comment.get('elapsed_time', '不明')
                similarity = comment.get('similarity', 0)

                context_parts.append(
                    f"{i}. ユーザー: {final_name} (ID: {user_id})"
                    f"\n   コメント: 「{comment['comment_text']}」"
                    f"\n   配信: {live_title} ({elapsed_time}) [類似度: {similarity:.3f}]"
                )

        # AI分析情報を追加
        if analyses:
            context_parts.append("\n【関連するAI分析】")
            for i, analysis in enumerate(analyses, 1):
                display_name = analysis.get('display_name', '')
                user_name = analysis.get('user_name', '')
                if display_name.startswith("ユーザー") and display_name.replace("ユーザー", "").isdigit():
                    final_name = user_name or display_name
                else:
                    final_name = display_name or user_name

                live_title = analysis.get('live_title', '不明な配信')
                model_used = analysis.get('model_used', '不明')
                similarity = analysis.get('similarity', 0)
                analysis_preview = analysis['analysis_text'][:150] + "..."

                context_parts.append(
                    f"{i}. ユーザー: {final_name} (ID: {analysis['user_id']}) の分析"
                    f"\n   モデル: {model_used}"
                    f"\n   要約: {analysis_preview}"
                    f"\n   配信: {live_title} [類似度: {similarity:.3f}]"
                )

        return "\n\n".join(context_parts)




    def _generate_answer(self, question: str, context: str) -> str:
        """LLMで回答生成"""
        try:
            # ✅ APIキーの読み込み
            config_path = os.path.join(os.path.dirname(__file__), "config", "ncv_special_config.json")
            api_key = None
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                api_key = config.get('api_settings', {}).get('openai_api_key', '')

            if not api_key:
                api_key = os.getenv('OPENAI_API_KEY')

            if not api_key:
                print("❌ OpenAI APIキーが設定されていません")
                return "❌ OpenAI APIキーが設定されていません"

            print(f"🔑 使用APIキー: {api_key[:8]}...{api_key[-4:]} (長さ: {len(api_key)})")
            client = openai.OpenAI(api_key=api_key, timeout=20.0)

            # ✅ system_prompt を強化
            system_prompt = """あなたはニコニコ生放送の分析専門家です。
提供されたコメント・ユーザー情報（特に user_id）を元に質問に答えてください。

重要:
- 回答には必ずユーザーの名前（display_name または user_name）と user_id を含める
- 「ユーザー◯◯」のような汎用名は避け、実際の user_name を優先
- コメント本文を引用して、なぜそう判断したのかを説明する
- 必要なら user_id を使って人物を明確化する
- 不足している情報は「不足している」と明示
- 簡潔かつ具体的に答える
"""
            user_prompt = f"""質問: {question}

    参考情報:
    {context}

    この情報をもとに、質問に対する明確で具体的な答えを出してください。
    """

            # ✅ 実際に送るプロンプトを丸ごと表示
            print("\n📝 --- LLMへ送信するプロンプト ---")
            print(f"[SYSTEM PROMPT]\n{system_prompt}\n")
            print(f"[USER PROMPT]\n{user_prompt}\n")
            print("📝 --- プロンプトここまで ---\n")

            print("🤖 AI回答生成中... (gpt-4o にリクエスト送信)")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.4
            )
            print("✅ OpenAI API呼び出し完了")

            answer = response.choices[0].message.content.strip()
            print("✅ AI回答生成完了")
            return answer

        except Exception as e:
            # エラー時もプロンプト内容を出力して原因を特定しやすくする
            print("❌ 回答生成エラーが発生しました")
            print("❌ 送信したプロンプト:")
            print(f"[SYSTEM PROMPT]\n{system_prompt}\n")
            print(f"[USER PROMPT]\n{user_prompt}\n")
            return f"回答生成中にエラーが発生しました: {str(e)}"



    
    def get_system_status(self) -> Dict:
        """RAGシステムの状況を取得"""
        
        status = {
            'vector_db_exists': os.path.exists(self.vector_db_path),
            'main_db_exists': os.path.exists(self.main_db_path),
            'total_comment_vectors': 0,
            'total_analysis_vectors': 0,
            'unique_broadcasts': 0,
            'unique_users': 0
        }
        
        if status['vector_db_exists']:
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
        
        return status

# 使用例・テスト用
if __name__ == "__main__":
    import sys

    rag = RAGSearchSystem()

    # システム状況確認
    status = rag.get_system_status()
    print("🔍 RAGシステム状況:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    # コマンドライン引数があればそれを質問に使う
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "面白いコメントをした人は誰ですか？"

    if status['total_comment_vectors'] > 0:
        print(f"\n📝 質問: {question}")
        answer = rag.search_and_answer(question)
        print(f"\n💡 回答:\n{answer}")
