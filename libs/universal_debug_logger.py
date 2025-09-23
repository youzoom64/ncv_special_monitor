import os
import json
import logging
import traceback
import inspect
from datetime import datetime
from typing import Any, Dict, Optional, Union
from functools import wraps
from logging.handlers import RotatingFileHandler

class UniversalDebugLogger:
    _global_instance = None
    _script_instances = {}
    
    def __init__(self, script_name: Optional[str] = None, use_global: bool = False):
        """
        script_name: None=自動検出, str=指定名, use_global=True=全スクリプト共有
        """
        self.use_global = use_global
        
        if use_global:
            self.script_name = "global"
            self.config_file = "global_debug_config.json"
        else:
            if script_name is None:
                # 呼び出し元のスクリプト名を自動取得
                frame = inspect.currentframe().f_back
                file_path = frame.f_globals.get('__file__', 'unknown')
                self.script_name = os.path.splitext(os.path.basename(file_path))[0]
            else:
                self.script_name = script_name
            self.config_file = f"{self.script_name}_debug_config.json"
        
        self.config = self.load_config()
        self.setup_paths()
        self.setup_logger()
        
    def setup_paths(self):
        """ログパスを設定"""
        base_dir = self.config["log_directory"]
        
        if self.use_global:
            self.log_dir = os.path.abspath(base_dir)
            self.log_file = os.path.join(self.log_dir, "global_debug.log")
        else:
            self.log_dir = os.path.join(base_dir, self.script_name)
            self.log_file = os.path.join(self.log_dir, f"{self.script_name}_debug.log")
        
        # 設定履歴用ディレクトリ
        self.config_history_dir = os.path.join(self.log_dir, "config_history")
        
    def load_config(self):
        """設定ファイルを読み込み、存在しない場合はデフォルト設定を作成"""
        default_config = {
            "log_directory": "debug_logs",
            "log_level": "DEBUG",
            "max_log_size_mb": 10,
            "backup_count": 5,
            "enable_console_output": True,
            "enable_file_output": True,
            "log_format": "%(asctime)s - [%(levelname)s] - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "encoding": "utf-8",
            "auto_trace_functions": False,
            "trace_return_values": True,
            "max_variable_length": 200,
            "enable_config_history": True,
            "config_version": "1.0.0",
            "created_at": datetime.now().isoformat()
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # デフォルト値でマージ
                merged_config = default_config.copy()
                merged_config.update(config)
                
                # 設定が更新された場合、履歴を保存
                if merged_config != config and merged_config.get("enable_config_history", True):
                    self.save_config_history(config, merged_config)
                
                return merged_config
                
            except Exception as e:
                print(f"設定ファイル読み込みエラー: {e}")
                return default_config
        else:
            # デフォルト設定ファイルを作成
            os.makedirs(os.path.dirname(self.config_file) if os.path.dirname(self.config_file) else ".", exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
    
    def save_config_history(self, old_config: dict, new_config: dict):
        """設定変更履歴を保存"""
        try:
            os.makedirs(self.config_history_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_file = os.path.join(self.config_history_dir, f"config_{timestamp}.json")
            
            history_data = {
                "timestamp": timestamp,
                "script_name": self.script_name,
                "old_config": old_config,
                "new_config": new_config,
                "changes": self.get_config_diff(old_config, new_config)
            }
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            print(f"設定履歴保存エラー: {e}")
    
    def get_config_diff(self, old_config: dict, new_config: dict) -> dict:
        """設定の差分を取得"""
        changes = {}
        all_keys = set(old_config.keys()) | set(new_config.keys())
        
        for key in all_keys:
            old_val = old_config.get(key, "<NOT_SET>")
            new_val = new_config.get(key, "<NOT_SET>")
            if old_val != new_val:
                changes[key] = {"old": old_val, "new": new_val}
        
        return changes
    
    def setup_logger(self):
        """ログ設定を初期化"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # ログフォーマット
        formatter = logging.Formatter(
            self.config["log_format"],
            datefmt=self.config["date_format"]
        )
        
        # ロガー設定
        logger_name = f'debug_logger_{self.script_name}'
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, self.config["log_level"]))
        self.logger.handlers.clear()
        
        # ファイルハンドラ（ローテーション対応）
        if self.config["enable_file_output"]:
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.config["max_log_size_mb"] * 1024 * 1024,
                backupCount=self.config["backup_count"],
                encoding=self.config["encoding"]
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # コンソール出力
        if self.config["enable_console_output"]:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def format_variables(self, variables: Dict[str, Any]) -> str:
        """変数を読みやすい形式にフォーマット"""
        max_length = self.config.get("max_variable_length", 200)
        formatted_vars = []
        
        for k, v in variables.items():
            try:
                var_str = f"{k}={repr(v)}"
                if len(var_str) > max_length:
                    var_str = f"{k}={repr(v)[:max_length-20]}...<truncated>"
                formatted_vars.append(var_str)
            except Exception as e:
                formatted_vars.append(f"{k}=<repr_error: {e}>")
        
        return " | ".join(formatted_vars)
    
    def log(self, level: str, message: str, variables: Optional[Dict[str, Any]] = None, 
            exception: Optional[Exception] = None, caller_info: bool = True):
        """デバッグログ出力"""
        log_parts = [message]
        
        # 呼び出し元情報
        if caller_info and not self.use_global:
            frame = inspect.currentframe().f_back.f_back
            filename = os.path.basename(frame.f_globals.get('__file__', 'unknown'))
            line_no = frame.f_lineno
            func_name = frame.f_code.co_name
            log_parts.append(f"Called from {filename}:{line_no} in {func_name}()")
        
        # 変数情報を追加
        if variables:
            var_info = self.format_variables(variables)
            log_parts.append(f"Variables: {var_info}")
        
        # 例外情報を追加
        if exception:
            log_parts.append(f"Exception: {str(exception)}")
            if level.upper() == "ERROR":
                log_parts.append(f"Traceback: {traceback.format_exc()}")
        
        log_message = " | ".join(log_parts)
        
        # ログレベルに応じて出力
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(log_message)
    
    def trace_function(self, func):
        """関数の実行をトレースするデコレータ"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.config.get("auto_trace_functions", False):
                func_args = f"args={args}, kwargs={kwargs}" if args or kwargs else "no arguments"
                self.log("DEBUG", f"Function START: {func.__name__}({func_args})", caller_info=False)
            
            try:
                result = func(*args, **kwargs)
                if self.config.get("auto_trace_functions", False) and self.config.get("trace_return_values", True):
                    self.log("DEBUG", f"Function END: {func.__name__} returned {repr(result)}", caller_info=False)
                return result
            except Exception as e:
                self.log("ERROR", f"Function EXCEPTION: {func.__name__}", exception=e, caller_info=False)
                raise
        
        return wrapper
    
    def get_logs(self, lines: int = 100) -> str:
        """最新ログを取得"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding=self.config["encoding"]) as f:
                    all_lines = f.readlines()
                    return ''.join(all_lines[-lines:])
            except Exception as e:
                return f"ログ読み込みエラー: {str(e)}"
        return "ログファイルが存在しません"
    
    def clear_logs(self):
        """ログファイルをクリア"""
        try:
            if os.path.exists(self.log_file):
                open(self.log_file, 'w', encoding=self.config["encoding"]).close()
                self.log("INFO", "ログファイルをクリアしました", caller_info=False)
        except Exception as e:
            self.log("ERROR", "ログクリアエラー", exception=e, caller_info=False)
    
    def get_config_history(self) -> list:
        """設定変更履歴を取得"""
        history = []
        if os.path.exists(self.config_history_dir):
            try:
                for filename in sorted(os.listdir(self.config_history_dir)):
                    if filename.startswith("config_") and filename.endswith(".json"):
                        filepath = os.path.join(self.config_history_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            history.append(json.load(f))
            except Exception as e:
                self.log("ERROR", "設定履歴取得エラー", exception=e)
        return history
    
    @classmethod
    def get_global_instance(cls):
        """全スクリプト共有のグローバルインスタンスを取得"""
        if cls._global_instance is None:
            cls._global_instance = cls(use_global=True)
        return cls._global_instance
    
    @classmethod
    def get_script_instance(cls, script_name: Optional[str] = None):
        """スクリプト専用インスタンスを取得"""
        if script_name is None:
            frame = inspect.currentframe().f_back
            file_path = frame.f_globals.get('__file__', 'unknown')
            script_name = os.path.splitext(os.path.basename(file_path))[0]
        
        if script_name not in cls._script_instances:
            cls._script_instances[script_name] = cls(script_name, use_global=False)
        return cls._script_instances[script_name]

# パブリックAPI関数群
def DEBUGLOG(message: str, level: str = "DEBUG", variables: Optional[Dict[str, Any]] = None, 
             exception: Optional[Exception] = None, use_global: bool = False):
    """デバッグログ出力（スクリプト別 or グローバル選択可能）"""
    if use_global:
        logger = UniversalDebugLogger.get_global_instance()
    else:
        logger = UniversalDebugLogger.get_script_instance()
    logger.log(level, message, variables, exception)

def GLOBAL_DEBUGLOG(message: str, level: str = "DEBUG", variables: Optional[Dict[str, Any]] = None, 
                    exception: Optional[Exception] = None):
    """グローバル共有ログ専用"""
    logger = UniversalDebugLogger.get_global_instance()
    logger.log(level, message, variables, exception)

def trace(use_global: bool = False):
    """関数トレース用デコレータ"""
    def decorator(func):
        if use_global:
            logger = UniversalDebugLogger.get_global_instance()
        else:
            logger = UniversalDebugLogger.get_script_instance()
        return logger.trace_function(func)
    return decorator

def get_debug_logs(lines: int = 100, use_global: bool = False) -> str:
    """ログ内容を取得"""
    if use_global:
        logger = UniversalDebugLogger.get_global_instance()
    else:
        logger = UniversalDebugLogger.get_script_instance()
    return logger.get_logs(lines)

def clear_debug_logs(use_global: bool = False):
    """ログをクリア"""
    if use_global:
        logger = UniversalDebugLogger.get_global_instance()
    else:
        logger = UniversalDebugLogger.get_script_instance()
    logger.clear_logs()

# 使用例とテスト
if __name__ == "__main__":
    # スクリプト個別ログ
    DEBUGLOG("スクリプト個別ログテスト")
    DEBUGLOG("変数付きログ", variables={"test_var": 123, "status": "OK"})
    
    # グローバル共有ログ
    GLOBAL_DEBUGLOG("グローバル共有ログテスト")
    GLOBAL_DEBUGLOG("システム全体の状態", variables={"total_scripts": 5, "active": True})
    
    # 関数トレース（個別）
    @trace()
    def test_function_local(x, y):
        DEBUGLOG("ローカル関数内処理", variables={"x": x, "y": y})
        return x + y
    
    # 関数トレース（グローバル）
    @trace(use_global=True)
    def test_function_global(x, y):
        GLOBAL_DEBUGLOG("グローバル関数内処理", variables={"x": x, "y": y})
        return x * y
    
    # テスト実行
    result1 = test_function_local(10, 20)
    result2 = test_function_global(5, 6)
    
    DEBUGLOG("処理完了", variables={"result1": result1, "result2": result2})
    
    # エラーテスト
    try:
        result = 10 / 0
    except Exception as e:
        DEBUGLOG("エラー発生テスト", level="ERROR", exception=e)
    
    print("\n=== スクリプト個別ログ ===")
    print(get_debug_logs(20))
    
    print("\n=== グローバル共有ログ ===")  
    print(get_debug_logs(20, use_global=True))