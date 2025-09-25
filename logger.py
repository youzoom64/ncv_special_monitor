import os
import logging
from datetime import datetime

class NCVSpecialLogger:
    def __init__(self, log_level=logging.DEBUG):
        self.log_dir = os.path.abspath("logs")
        self.log_file = os.path.join(self.log_dir, "ncv_special_monitor.log")
        self.log_level = log_level
        self.setup_logger()
        
    def setup_logger(self):
        """ログ設定を初期化"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # ログフォーマット
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # ロガー設定
        self.logger = logging.getLogger('ncv_special_monitor')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # 既存ハンドラをクリア
        
        # ファイルハンドラ
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(self.log_level)
        self.logger.addHandler(file_handler)
        
        # コンソール出力
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(self.log_level)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        self.logger.info(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def get_recent_logs(self, lines=50):
        """最近のログを取得"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    return ''.join(all_lines[-lines:])
            except Exception as e:
                return f"ログ読み込みエラー: {str(e)}"
        return "ログファイルが存在しません"
    
    def clear_logs(self):
        """ログファイルをクリア"""
        try:
            if os.path.exists(self.log_file):
                open(self.log_file, 'w').close()
                self.info("ログファイルをクリアしました")
        except Exception as e:
            self.error(f"ログクリアエラー: {str(e)}")