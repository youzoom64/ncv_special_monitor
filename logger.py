import os
import logging
from datetime import datetime

class NCVSpecialLogger:
    def __init__(self):
        self.log_dir = os.path.abspath("logs")
        self.log_file = os.path.join(self.log_dir, "ncv_special_monitor.log")
        self.setup_logger()
        
    def setup_logger(self):
        """ログ設定を初期化"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # ログフォーマットを設定import os
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
        
        # ファイルハンドラ
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(self.log_level)  # ★ DEBUG も出す

        # ロガー設定
        self.logger = logging.getLogger('ncv_special_monitor')
        self.logger.setLevel(self.log_level)  # ★ DEBUG 有効化

        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
        
        # コンソール出力
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(self.log_level)  # ★ DEBUG も出す
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        self.logger.info(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def debug(self, message):
        self.logger.debug(message)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # ファイルハンドラを設定
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # ロガーを設定
        self.logger = logging.getLogger('ncv_special_monitor')
        self.logger.setLevel(logging.INFO)
        
        # 既存のハンドラをクリア
        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
        
        # コンソール出力も追加
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        """INFOレベルでログ記録"""
        self.logger.info(message)
    
    def error(self, message):
        """ERRORレベルでログ記録"""
        self.logger.error(message)
    
    def warning(self, message):
        """WARNINGレベルでログ記録"""
        self.logger.warning(message)
    
    def debug(self, message):
        """DEBUGレベルでログ記録"""
        self.logger.debug(message)