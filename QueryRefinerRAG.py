# QueryRefinerRAG.py
import sqlite3
import numpy as np
import os
from typing import List, Dict, Optional
import openai
import json

# いつでもこのIDだけを見る
TARGET_USER_ID = "21639740"


class RAGSearchSystem:
    def __init__(self, main_db_path: str = "data/ncv_monitor.db", vector_db_path: str = "data/vectors.db"):
        self.main_db_path = main_db_path
        self.vector_db_path = vector_db_path

        # DB存在チェック
        if not os.path.exists(self.vector_db_path):
            print(f"⚠️ ベクトルDBが見つかりません: {self.vector_db_path}")
            print("先にベクトル化を実行してください")

        if not os.path.exists(self.main_db_path):
            print(f"⚠️ メインDBが見つかりません: {self.main_db_path}")

        # APIキー読み込み
        config_path = os.path.join(os.path.dirname(__file__), "config", "ncv_special_config.json")
        api_key: Optional[str] = None
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                api_key = cfg.get('api_settings', {}).get('openai_api_key', '')
            except Exception:
                api_key = None

        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            raise RuntimeError("❌ OpenAI APIキーが設定されていません")

        # OpenAI クライアント
        self.client = openai.OpenAI(api_key=api_key, timeout=20.0)

    # --- 前処理（質問整形のみ：mini 1回） ---
    def preprocess_question(self, question: str) -> str:
        """
        入力の質問文を、ベクトル検索向けの短い検索語に整形して返す。
        可能な限り名詞・キーワード中心、10〜20文字程度を目安。
        """
        system_prompt = (
            "あなたは検索クエリ変換エージェントです。"
            "入力された質問文を、ベクトル検索に適した短い文に変換してください。"
            "ルール:"
            "1. 疑問詞や助詞を削除してよいが、意味上の主語・対象・行為は必ず残す。"
            "2. 固有名詞は省略せず保持する。"
            "3. 曖昧な人物参照（この人、こいつ等）は user_id=21639740 に置き換える。"
            "4. 出力は一文のみで、余計な説明は不要。"
            "5. 出力形式は自然な短文でよい（単語の羅列は禁止）。"
        )
        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=50,
                temperature=0
            )
            refined = (resp.choices[0].message.content or "").strip()
            if not refined:
                refined = question
        except Exception:
            refined = question

        print(f"🧭 質問整形: {question} → {refined}")
        return refined

    # --- ベクトル化 ---
    def _get_embedding(self, text: str) -> np.ndarray:
        resp = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return np.array(resp.data[0].embedding, dtype=np.float32)

    # --- 類似コメント検索（常に TARGET_USER_ID でフィルタ） ---
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

            # 追加情報付与（名前・枠タイトル等）
            results = self._enrich_comment_results(results)

            print(f"💬 類似コメント: {len(results)}件 (user_id={TARGET_USER_ID})")
            return results

        except Exception as e:
            print(f"❌ コメント検索エラー: {e}")
            return []

    # --- 類似AI分析検索（常に TARGET_USER_ID でフィルタ） ---
    def _search_similar_analyses(self, query_vector: np.ndarray, top_k: int) -> List[Dict]:
        results: List[Dict] = []
        try:
            with sqlite3.connect(self.vector_db_path) as vconn:
                cur = vconn.cursor()
                cur.execute("""
                    SELECT av.analysis_id, av.user_id, av.analysis_text, av.vector_data, av.broadcast_id
                    FROM analysis_vectors av
                    WHERE av.user_id = ?
                """, (TARGET_USER_ID,))
                rows = cur.fetchall()

            for analysis_id, uid, analysis_text, vector_blob, broadcast_id in rows:
                stored = np.frombuffer(vector_blob, dtype=np.float32)
                sim = self._cosine_similarity(query_vector, stored)
                results.append({
                    "analysis_id": analysis_id,
                    "user_id": uid,
                    "analysis_text": analysis_text,
                    "broadcast_id": broadcast_id,
                    "similarity": sim,
                })

            results.sort(key=lambda x: x["similarity"], reverse=True)
            results = results[:top_k]

            # 追加情報付与
            results = self._enrich_analysis_results(results)

            print(f"🤖 類似AI分析: {len(results)}件 (user_id={TARGET_USER_ID})")
            return results

        except Exception as e:
            print(f"❌ AI分析検索エラー: {e}")
            return []

    # --- 追加情報付与：コメント ---
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

    # --- 追加情報付与：AI分析 ---
    def _enrich_analysis_results(self, items: List[Dict]) -> List[Dict]:
        if not items:
            return items
        try:
            ids = [i["analysis_id"] for i in items]
            placeholders = ",".join("?" for _ in ids)
            with sqlite3.connect(self.main_db_path) as conn:
                cur = conn.cursor()
                cur.execute(f"""
                    SELECT a.id, a.model_used, a.comment_count, a.analysis_date,
                           b.lv_value, b.live_title, b.start_time,
                           su.display_name
                    FROM ai_analyses a
                    JOIN broadcasts b ON a.broadcast_id = b.id
                    LEFT JOIN special_users su ON a.user_id = su.user_id
                    WHERE a.id IN ({placeholders})
                """, ids)
                meta = {row[0]: {
                    "model_used": row[1],
                    "comment_count": row[2],
                    "analysis_date": row[3],
                    "lv_value": row[4],
                    "live_title": row[5],
                    "start_time": row[6],
                    "display_name": row[7],
                } for row in cur.fetchall()}

            for it in items:
                info = meta.get(it["analysis_id"], {})
                it.update(info)
            return items
        except Exception as e:
            print(f"⚠️ 分析付随情報の取得に失敗: {e}")
            return items

    # --- 類似度 ---
    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        dot = float(np.dot(v1, v2))
        n1 = float(np.linalg.norm(v1))
        n2 = float(np.linalg.norm(v2))
        return dot / (n1 * n2) if n1 and n2 else 0.0

    # --- コンテキスト構築 ---
    def _build_context(self, comments: List[Dict], analyses: List[Dict]) -> str:
        parts: List[str] = []

        if comments:
            parts.append("【関連するコメント】")
            for i, c in enumerate(comments, 1):
                disp = (c.get("display_name") or c.get("user_name") or "").strip()
                if disp.startswith("ユーザー") and disp.replace("ユーザー", "").isdigit():
                    # ニコ生の汎用名は user_name を優先
                    disp = (c.get("user_name") or disp).strip()

                parts.append(
                    f"{i}. ユーザー: {disp or '不明'} (ID: {c.get('user_id')})"
                    f"\n   コメント: 「{c.get('comment_text','')}」"
                    f"\n   配信: {c.get('live_title','不明な配信')} / 経過: {c.get('elapsed_time','?')} [類似度: {c.get('similarity',0):.3f}]"
                )

        if analyses:
            parts.append("\n【関連するAI分析】")
            for i, a in enumerate(analyses, 1):
                disp = (a.get("display_name") or "").strip()
                preview = (a.get("analysis_text") or "")[:150] + "..."
                parts.append(
                    f"{i}. ユーザー: {disp or '不明'} (ID: {a.get('user_id')}) の分析"
                    f"\n   モデル: {a.get('model_used','不明')} / 件数: {a.get('comment_count','?')} / 日付: {a.get('analysis_date','?')}"
                    f"\n   要約: {preview}"
                    f"\n   配信: {a.get('live_title','不明な配信')} [類似度: {a.get('similarity',0):.3f}]"
                )

        return "\n\n".join(parts)

    # --- 回答生成 ---
    def _generate_answer(self, question: str, context: str) -> str:
        system_prompt = (
            "あなたはニコニコ生放送の分析担当です。"
            "与えられたコンテキスト（コメント・分析）にのみ基づいて、簡潔かつ根拠付きで回答してください。"
            "必ず user_id を明記し、引用箇所を根拠として示してください。"
            "不足がある場合は『不足している』と述べてください。"
        )
        user_prompt = f"質問: {question}\n\n参考情報:\n{context}\n\nこの情報だけで回答してください。"

        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.4
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            return f"回答生成中にエラー: {e}"

    # --- メイン ---
    def search_and_answer(self, question: str, top_k: int = 10) -> str:
        print(f"🔍 質問: {question}")
        print(f"🧭 固定 user_id={TARGET_USER_ID} を使用")

        # 1) 質問整形 → 2) ベクトル化
        refined = self.preprocess_question(question)
        query_vec = self._get_embedding(refined)

        # 3) 検索（コメントのみ10件）
        comments = self._search_similar_comments(query_vec, top_k)
        analyses = []  # AI分析は使用しない

        # 4) 回答生成
        context = self._build_context(comments, analyses)
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
