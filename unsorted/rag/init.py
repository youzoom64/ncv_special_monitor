# rag/__init__.py（修正版）
"""
RAG (Retrieval-Augmented Generation) システム

基本的な使用方法:
    from rag import RAGSystem
    
    rag = RAGSystem()
    result = rag.query("質問内容", user_id="12345")
"""

from .rag_core import RAGSystem

__all__ = ['RAGSystem']  # ← ★修正: __all__
__version__ = '1.0.0'    # ← ★修正: __version__