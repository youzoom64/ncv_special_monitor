# QueryRefinerRAG.py
import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

import sqlite3
import numpy as np
from typing import List, Dict, Optional
import json
from datetime import datetime

TARGET_USER_ID = "21639740"

class AIClient:
    def __init__(self, model_type: str, api_key: str):
        self.model_type = model_type
        self.api_key = api_key
        
        if model_type.startswith("openai"):
            import openai
            self.client = openai.OpenAI(api_key=api_key, timeout=20.0)
        elif model_type.startswith("google"):
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.genai = genai
            self.client = genai.GenerativeModel('gemini-2.5-flash')
        else:
            raise ValueError(f"サポートされていないモデル: {model_type}")
    
    def chat_completion(self, messages: List[Dict], max_tokens: int = 800, temperature: float = 0.4) -> str:
        try:
            if self.model_type.startswith("openai"):
                model = "gpt-4o" if self.model_type == "openai-gpt4o" else "gpt-4o-mini"
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return (resp.choices[0].message.content or "").strip()
            
            elif self.model_type.startswith("google"):
                if len(messages) >= 2:
                    system_content = messages[0].get("content", "")
                    user_content = messages[1].get("content", "")
                    prompt = f"{system_content}\n\n{user_content}"
                else:
                    prompt = messages[0].get("content", "")
                
                response = self.client.generate_content(prompt)
                return response.text.strip()
                
        except Exception as e:
            return f"AI処理エラー: {e}"

class RAGSearchSystem:
    def __init__(self, main_db_path: str = "data/ncv_monitor.db", vector_db_path: str = "data/vectors.db"):
        self.main_db_path = main_db_path
        self.vector_db_path = vector_db_path
        
        if not os.path.exists(self.vector_db_path):
            print(f"⚠️ ベクトルDBが見つかりません: {self.vector_db_path}")

        if not os.path.exists(self.main_db_path):
            print(f"⚠️ メインDBが見つかりません: {self.main_db_path}")

        self.config = self._load_config()
        
        # 各処理用のクライアントを個別に初期化
        self.query_client = self._init_query_client()
        self.answer_client = self._init_answer_client()
        self.embedding_client = self._init_embedding_client()

    def _load_config(self) -> Dict:
        config_path = os.path.join(os.path.dirname(__file__), "config", "ncv_special_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"設定ファイル読み込みエラー: {e}")
        return {}
    
    def _init_query_client(self) -> AIClient:
        """質問整形用AIクライアント"""
        api_settings = self.config.get('api_settings', {})
        model_type = api_settings.get('query_ai_model', 'openai-gpt4o-mini')
        
        if model_type.startswith("openai") or model_type in ["gpt-4o", "gpt-4o-mini"]:
            api_key = api_settings.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
            if not model_type.startswith("openai"):
                model_type = f"openai-{model_type}"
        elif model_type.startswith("google") or "gemini" in model_type:
            api_key = api_settings.get('google_api_key') or os.getenv('GOOGLE_API_KEY')
            if not model_type.startswith("google"):
                model_type = f"google-{model_type}"
        else:
            raise RuntimeError(f"❌ 未対応のクエリモデル: {model_type}")
        
        if not api_key:
            raise RuntimeError("❌ APIキーが設定されていません")
        
        print(f"🔍 質問整形モデル: {model_type}")
        return AIClient(model_type, api_key)
    
    def _init_answer_client(self) -> AIClient:
        """回答生成用AIクライアント"""
        api_settings = self.config.get('api_settings', {})
        model_type = api_settings.get('answer_ai_model', 'openai-gpt4o')
        
        if model_type.startswith("openai") or model_type in ["gpt-4o", "gpt-4o-mini"]:
            api_key = api_settings.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
            if not model_type.startswith("openai"):
                model_type = f"openai-{model_type}"
        elif model_type.startswith("google") or "gemini" in model_type:
            api_key = api_settings.get('google_api_key') or os.getenv('GOOGLE_API_KEY')
            if not model_type.startswith("google"):
                model_type = f"google-{model_type}"
        else:
            raise RuntimeError(f"❌ 未対応の回答モデル: {model_type}")
        
        if not api_key:
            raise RuntimeError("❌ APIキーが設定されていません")
        
        print(f"💡 回答生成モデル: {model_type}")
        return AIClient(model_type, api_key)
    
    def _init_embedding_client(self):
        """埋め込み用クライアント（設定から選択）"""
        api_settings = self.config.get('api_settings', {})
        embedding_model = api_settings.get('embedding_model', 'text-embedding-3-small')
        
        if embedding_model in ['text-embedding-3-small', 'text-embedding-3-large', 'text-embedding-ada-002']:
            # OpenAI Embedding
            api_key = api_settings.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise RuntimeError("❌ OpenAI APIキーが設定されていません")
            
            import openai
            self.embedding_client_type = 'openai'
            self.embedding_model = embedding_model
            self.openai_client = openai.OpenAI(api_key=api_key)
            print(f"🔗 埋め込みモデル: {embedding_model} (OpenAI)")
            
        elif embedding_model in ['models/text-embedding-004', 'models/embedding-001']:
            # Google Embedding
            api_key = api_settings.get('google_api_key') or os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise RuntimeError("❌ Google APIキーが設定されていません")
            
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.embedding_client_type = 'google'
            self.embedding_model = embedding_model
            self.genai = genai
            print(f"🔗 埋め込みモデル: {embedding_model} (Google)")
            
        else:
            raise RuntimeError(f"❌ 未対応の埋め込みモデル: {embedding_model}")

    def preprocess_question(self, question: str) -> str:
        messages = [
            {
                "role": "system", 
                "content": """あなたは検索クエリ変換エージェントです。
入力された質問文を、ベクトル検索に適した短い文に変換してください。
ルール:
1. 疑問詞や助詞を削除してよいが、意味上の主語・対象・行為は必ず残す
2. 固有名詞は省略せず保持する
3. 曖昧な人物参照（この人、こいつ等）は user_id=21639740 に置き換える
4. 出力は一文のみで、余計な説明は不要
5. 出力形式は自然な短文でよい（単語の羅列は禁止）"""
            },
            {"role": "user", "content": question}
        ]
        
        refined = self.query_client.chat_completion(messages, max_tokens=50, temperature=0)
        if not refined or "エラー" in refined:
            refined = question
        
        print(f"🧭 質問整形: {question} → {refined}")
        return refined

    def _get_embedding(self, text: str) -> np.ndarray:
        """設定に基づく埋め込み生成"""
        try:
            if self.embedding_client_type == 'openai':
                resp = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                return np.array(resp.data[0].embedding, dtype=np.float32)
            
            elif self.embedding_client_type == 'google':
                result = self.genai.embed_content(
                    model=self.embedding_model,
                    content=text
                )
                return np.array(result['embedding'], dtype=np.float32)
                
        except Exception as e:
            print(f"埋め込み生成エラー: {e}")
            # デフォルト次元数を動的に決定
            if self.embedding_client_type == 'openai':
                return np.zeros(1536, dtype=np.float32)
            else:
                return np.zeros(768, dtype=np.float32)

    def _search_similar_comments(self, query_vector: np.ndarray, top_k: int) -> List[Dict]:
        results: List[Dict] = []
        try:
            with sqlite3.connect(self.vector_db_path) as vconn:
                cur = vconn.cursor()
                cur.execute("""
                    SELECT cv.comment_id, cv.user_id, cv.comment_text, cv.vector_data, cv.broadcast_id
                    FROM comment_vectors cv
                    WHERE cv.user_id = ?
                """, (TARGET_USER_ID,))
                rows = cur.fetchall()

            for comment_id, uid, comment_text, vector_blob, broadcast_id in rows:
                stored = np.frombuffer(vector_blob, dtype=np.float32)
                sim = self._cosine_similarity(query_vector, stored)
                results.append({
                    "comment_id": comment_id,
                    "user_id": uid,
                    "comment_text": comment_text,
                    "broadcast_id": broadcast_id,
                    "similarity": sim,
                })

            results.sort(key=lambda x: x["similarity"], reverse=True)
            results = results[:top_k]
            results = self._enrich_comment_results(results)

            print(f"💬 類似コメント: {len(results)}件 (user_id={TARGET_USER_ID})")
            return results

        except Exception as e:
            print(f"❌ コメント検索エラー: {e}")
            return []

    def _enrich_comment_results(self, items: List[Dict]) -> List[Dict]:
        if not items:
            return items
        try:
            ids = [i["comment_id"] for i in items]
            placeholders = ",".join("?" for _ in ids)
            with sqlite3.connect(self.main_db_path) as conn:
                cur = conn.cursor()
                cur.execute(f"""
                    SELECT c.id, c.user_name, c.timestamp, c.elapsed_time,
                           b.lv_value, b.live_title, b.start_time,
                           su.display_name
                    FROM comments c
                    JOIN broadcasts b ON c.broadcast_id = b.id
                    LEFT JOIN special_users su ON c.user_id = su.user_id
                    WHERE c.id IN ({placeholders})
                """, ids)
                meta = {row[0]: {
                    "user_name": row[1],
                    "timestamp": row[2],
                    "elapsed_time": row[3],
                    "lv_value": row[4],
                    "live_title": row[5],
                    "start_time": row[6],
                    "display_name": row[7]
                } for row in cur.fetchall()}

            for it in items:
                info = meta.get(it["comment_id"], {})
                it.update(info)
            return items
        except Exception as e:
            print(f"⚠️ コメント付随情報の取得に失敗: {e}")
            return items

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        dot = float(np.dot(v1, v2))
        n1 = float(np.linalg.norm(v1))
        n2 = float(np.linalg.norm(v2))
        return dot / (n1 * n2) if n1 and n2 else 0.0

    def _build_context(self, comments: List[Dict]) -> str:
        parts: List[str] = []

        if comments:
            parts.append("【関連するコメント】")
            for i, c in enumerate(comments, 1):
                disp = (c.get("display_name") or c.get("user_name") or "").strip()
                if disp.startswith("ユーザー") and disp.replace("ユーザー", "").isdigit():
                    disp = (c.get("user_name") or disp).strip()

                start_time_str = "不明"
                if c.get("start_time"):
                    try:
                        start_time_str = datetime.fromtimestamp(int(c["start_time"])).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        start_time_str = "不明"

                parts.append(
                    f"{i}. ユーザー: {disp or '不明'} (ID: {c.get('user_id')})"
                    f"\n   コメント: 「{c.get('comment_text','')}」"
                    f"\n   配信: {c.get('live_title','不明な配信')} / 開始: {start_time_str} / 経過: {c.get('elapsed_time','?')} [類似度: {c.get('similarity',0):.3f}]"
                )

        return "\n\n".join(parts)

    def _generate_answer(self, question: str, context: str) -> str:
        messages = [
            {
                "role": "system",
                "content": """あなたはニコニコ生放送の分析案内担当です。
与えられたコンテキスト（コメント・分析）にのみ基づいて、詳細かつ根拠付きで回答してください。
回答には以下を必ず含めてください：
1. user_id と名前を明記
2. 具体的なコメント内容を引用
3. 放送タイトル名
4. 配信開始日時
5. 配信開始からの経過時間
6. どの発言がいつの配信でのものかを明確に示す

各コメントについて3つ程度用意し、「配信『タイトル名』(開始: 日時)の経過XX分でのコメント『内容』」の形式で詳細を50文字程度で記載してください。
不足がある場合は『不足している』と述べてください。
ずんだもんの口調で答えてください。語尾は必ずなのだでお願いします。
全体で300文字程度以内にお願いします。
"""
            },
            {
                "role": "user", 
                "content": f"質問: {question}\n\n参考情報:\n{context}\n\nこの情報だけで回答してください。"
            }
        ]
        
        return self.answer_client.chat_completion(messages)

    def search_and_answer(self, question: str, top_k: int = 10) -> str:
        print(f"🔍 質問: {question}")
        print(f"🧭 固定 user_id={TARGET_USER_ID} を使用")

        refined = self.preprocess_question(question)
        query_vec = self._get_embedding(refined)
        comments = self._search_similar_comments(query_vec, top_k)

        context = self._build_context(comments)
        if not context.strip():
            print("🧭 検索結果: 0件")
            return "🤷 関連情報なし"

        print(f"📊 検索結果: コメント{len(comments)}件")
        return self._generate_answer(question, context)


if __name__ == "__main__":
    import sys
    rag = RAGSearchSystem()

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "この人なにが好き？"

    ans = rag.search_and_answer(question)
    print(f"\n💡 回答:\n{ans}")