# rag/statistical.py（正しい修正版）
import sqlite3
from typing import Dict, Optional, List

class StatisticalAnalyzer:
    """統計分析機能"""
    
    def __init__(self, db_path: str):  # ← 修正: __init__
        self.db_path = db_path
    
    def analyze(self, question: str, user_id: Optional[str], 
                broadcast_id: Optional[int]) -> Dict:
        """統計分析実行"""
        
        print(f"📊 統計分析: {question}")
        
        if user_id:
            stats = self._get_user_statistics(user_id)
            answer = self._generate_user_stats_answer(question, stats, user_id)
        else:
            stats = self._get_general_statistics()
            answer = self._generate_general_stats_answer(question, stats)
        
        return {
            'answer': answer,
            'statistics': stats,
            'query_type': 'statistical'
        }
    
    def _get_user_statistics(self, user_id: str) -> Dict:  # ← 修正: _get_user_statistics
        """ユーザー統計取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # よく出現する配信者TOP5
            cursor.execute("""
                SELECT b.broadcaster, b.owner_name, COUNT(*) as comment_count
                FROM comments c
                JOIN broadcasts b ON c.broadcast_id = b.id
                WHERE c.user_id = ? AND c.is_special_user = 1
                GROUP BY b.broadcaster, b.owner_name
                ORDER BY comment_count DESC
                LIMIT 5
            """, (user_id,))
            
            top_broadcasters = []
            for row in cursor.fetchall():
                broadcaster, owner_name, count = row
                top_broadcasters.append({
                    'broadcaster': broadcaster or owner_name,
                    'comment_count': count
                })
            
            return {'top_broadcasters': top_broadcasters}
    
    def _get_general_statistics(self) -> Dict:  # ← 修正: _get_general_statistics
        """全体統計取得"""
        return {'message': '全体統計は今後実装予定'}
    
    def _generate_user_stats_answer(self, question: str, stats: Dict, user_id: str) -> str:  # ← 修正: _generate_user_stats_answer
        """ユーザー統計の回答生成"""
        top_broadcasters = stats.get('top_broadcasters', [])
        
        if not top_broadcasters:
            return f"ユーザー{user_id}の活動データが見つかりませんでした。"
        
        answer_parts = [f"ユーザー{user_id}がよく出現する配信者:"]
        for i, broadcaster in enumerate(top_broadcasters, 1):
            answer_parts.append(f"{i}. {broadcaster['broadcaster']} ({broadcaster['comment_count']}コメント)")
        
        return "\n".join(answer_parts)
    
    def _generate_general_stats_answer(self, question: str, stats: Dict) -> str:  # ← 修正: _generate_general_stats_answer
        """全体統計の回答生成"""
        return "全体統計機能は今後実装予定です。"