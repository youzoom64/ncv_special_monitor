import os
import time
import re
import threading
from datetime import datetime
from pathlib import Path

class NCVFolderMonitor:
    def __init__(self, config_manager, logger, broadcast_detector):
        self.config_manager = config_manager
        self.logger = logger
        self.broadcast_detector = broadcast_detector
        self.running = False
        self.thread = None
        self.monitored_xmls = {}  # XMLファイルの監視状態
        
    def start_monitoring(self):
        """監視開始"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            self.logger.info("NCVフォルダ監視を開始しました")
    
    def stop_monitoring(self):
        """監視停止"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        self.logger.info("NCVフォルダ監視を停止しました")
    
  
    def _scan_for_new_xmls(self, ncv_path):
        """新規XMLファイルをスキャン"""
        try:
            for subfolder in os.listdir(ncv_path):
                subfolder_path = os.path.join(ncv_path, subfolder)
                
                if not os.path.isdir(subfolder_path):
                    continue
                
                for filename in os.listdir(subfolder_path):
                    if self._is_ncv_xml_file(filename):
                        xml_path = os.path.join(subfolder_path, filename)
                        
                        if self.config_manager.is_processed(xml_path):
                            continue
                        
                        if xml_path in self.monitored_xmls:
                            continue
                        
                        self.logger.debug(f"[DEBUG] 新規XML検出: {xml_path}")
                        self._start_xml_monitoring(xml_path, subfolder)
                        
        except Exception as e:
            self.logger.error(f"XMLスキャンエラー: {str(e)}")
    
    def _is_ncv_xml_file(self, filename):
        """NCVのXMLファイルかチェック（より厳密なパターン）"""
        # 例：ncvLog_lv123456_20250913_123045.xml
        pattern = r'^ncvLog_lv\d+_\d{8}_\d{6}\.xml$'
        return re.match(pattern, filename) is not None

    def _monitor_loop(self):
        """監視ループ"""
        while self.running:
            try:
                config = self.config_manager.load_config()
                
                if not config.get("monitor_enabled", True):
                    self.logger.debug("[DEBUG] 監視無効 → 60秒待機")
                    time.sleep(60)
                    continue
                
                ncv_path = config.get("ncv_folder_path", "")
                if not os.path.exists(ncv_path):
                    self.logger.warning(f"NCVフォルダが存在しません: {ncv_path}")
                    time.sleep(60)
                    continue
                
                self.logger.debug(f"[DEBUG] NCVフォルダスキャン開始: {ncv_path}")
                
                # 新規XMLファイルを検索
                self._scan_for_new_xmls(ncv_path)
                
                self.logger.debug(f"[DEBUG] 現在監視中XML数: {len(self.monitored_xmls)}")
                
                # ★ 監視中XMLの詳細を出力
                for xml_path, info in self.monitored_xmls.items():
                    self.logger.debug(f"[DEBUG] 監視中: {info['lv_value']} - {xml_path}")
                
                # 既存の監視中XMLをチェック
                self._check_monitored_xmls()
                
                self.logger.debug("[DEBUG] 次回スキャンまで10秒待機")
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"監視ループエラー: {str(e)}")
                time.sleep(60)
    
    def _start_xml_monitoring(self, xml_path, subfolder_name):
        """XMLファイルの監視を開始"""
        try:
            lv_value = self._extract_lv_value(xml_path)
            if not lv_value:
                self.logger.warning(f"lv値を抽出できません: {xml_path}")
                return
            
            self.monitored_xmls[xml_path] = {
                'lv_value': lv_value,
                'subfolder_name': subfolder_name,
                'start_time': datetime.now(),
                'status': 'monitoring'
            }
            
            self.logger.info(f"新規XML検出・監視開始: {lv_value} ({subfolder_name})")
            
            self.broadcast_detector.start_detection(xml_path, lv_value, subfolder_name)
            
        except Exception as e:
            self.logger.error(f"XML監視開始エラー: {str(e)}")
    
    def _extract_lv_value(self, xml_path):
        filename = os.path.basename(xml_path)
        match = re.search(r'lv\d+', filename)
        return match.group() if match else None
    
    def _check_monitored_xmls(self):
        """監視中XMLファイルの状態をチェック"""
        for xml_path in list(self.monitored_xmls.keys()):
            monitor_info = self.monitored_xmls[xml_path]
            
            if not os.path.exists(xml_path):
                self.logger.warning(f"監視中XMLファイルが削除されました: {xml_path}")
                del self.monitored_xmls[xml_path]
                continue
            
            elapsed_hours = (datetime.now() - monitor_info['start_time']).total_seconds() / 3600
            if elapsed_hours > 24:
                self.logger.warning(f"長時間監視中のXMLファイル: {xml_path}")
    
    def xml_processing_completed(self, xml_path):
        """XMLの処理完了通知"""
        if xml_path in self.monitored_xmls:
            del self.monitored_xmls[xml_path]
            self.logger.info(f"XML処理完了・監視終了: {xml_path}")
    
    def get_monitoring_status(self):
        return {
            'running': self.running,
            'monitored_count': len(self.monitored_xmls),
            'monitored_files': list(self.monitored_xmls.keys())
        }
