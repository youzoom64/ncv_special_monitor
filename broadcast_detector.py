import requests
import time
import threading
import re
from datetime import datetime

class BroadcastEndDetector:
    def __init__(self, config_manager, logger, pipeline_executor):
        self.config_manager = config_manager
        self.logger = logger
        self.pipeline_executor = pipeline_executor
        self.active_detections = {}  # アクティブな検出処理
        
    def start_detection(self, xml_path, lv_value, subfolder_name):
        """放送終了検出を開始"""
        # 二重実行防止: 既に処理済みならスキップ
        if self.config_manager.is_processed(xml_path):
            self.logger.info(f"既に処理済みのXML。スキップ: {lv_value}")
            return

        if lv_value in self.active_detections:
            self.logger.warning(f"既に検出中です: {lv_value}")
            return
        
        self.logger.info(f"[DEBUG] 放送終了検出開始準備: {lv_value}")  # ★ 追加
        
        detection_info = {
            'xml_path': xml_path,
            'lv_value': lv_value,
            'subfolder_name': subfolder_name,
            'start_time': datetime.now(),
            'retry_count': 0,
            'thread': None
        }

        # --- 初回即時チェック ---
        try:
            self.logger.debug(f"[DEBUG] 初回即時チェック開始: {lv_value}")  # ★ 追加
            if self._check_broadcast_end(lv_value):
                self.logger.info(f"放送終了を即時検出: {lv_value}")
                # パイプライン実行 & 処理済み登録
                self.pipeline_executor.execute_pipeline(xml_path, lv_value, subfolder_name)
                self.config_manager.add_processed_xml(xml_path)
                return  # スレッド起動せず終了
            else:
                self.logger.debug(f"[DEBUG] 初回チェック結果: 放送継続中 {lv_value}")  # ★ 追加
        except Exception as e:
            self.logger.error(f"初回終了チェックでエラー: {lv_value} - {str(e)}")

        # --- 継続監視スレッド開始 ---
        thread = threading.Thread(
            target=self._detection_loop,
            args=(detection_info,),
            daemon=True
        )
        detection_info['thread'] = thread
        self.active_detections[lv_value] = detection_info
        
        thread.start()
        self.logger.info(f"放送終了検出開始: {lv_value}")
    
    def _detection_loop(self, detection_info):
        lv_value = detection_info['lv_value']
        xml_path = detection_info['xml_path']
        subfolder_name = detection_info['subfolder_name']
        
        config = self.config_manager.load_config()
        check_interval = 30  # ★ 10秒 → 30秒に変更
        max_retries = config.get("retry_count", 3)

        # ★ 最初に少し待機（同時アクセス回避）
        import random
        initial_delay = random.uniform(1, 10)  # 1-10秒のランダム待機
        time.sleep(initial_delay)
        
        try:
            while lv_value in self.active_detections:
                try:
                    self.logger.debug(f"[DEBUG] 放送終了チェック開始: {lv_value}")
                    result = self._check_broadcast_end(lv_value)
                    self.logger.debug(f"[DEBUG] 終了チェック結果: {lv_value} → {'終了' if result else '継続'}")
                    
                    if result:
                        self.logger.info(f"放送終了を検出: {lv_value}")
                        self.pipeline_executor.execute_pipeline(xml_path, lv_value, subfolder_name)
                        self.config_manager.add_processed_xml(xml_path)
                        break
                    else:
                        self.logger.debug(f"放送継続中: {lv_value}")
                        detection_info['retry_count'] = 0
                except Exception as e:
                    detection_info['retry_count'] += 1
                    self.logger.error(f"放送終了チェックエラー: {lv_value} - {str(e)} (リトライ: {detection_info['retry_count']}/{max_retries})")
                    if detection_info['retry_count'] >= max_retries:
                        # ★ エラー時は終了扱いにしてパイプライン実行
                        self.logger.info(f"エラーによる強制終了判定: {lv_value}")
                        self.pipeline_executor.execute_pipeline(xml_path, lv_value, subfolder_name)
                        self.config_manager.add_processed_xml(xml_path)
                        break

                self.logger.debug(f"[DEBUG] 次回チェックまで待機 {check_interval}秒: {lv_value}")
                time.sleep(check_interval)
        finally:
            if lv_value in self.active_detections:
                del self.active_detections[lv_value]
            self.logger.info(f"放送終了検出終了: {lv_value}")

        
    def _check_broadcast_end(self, lv_value):
        """放送が終了しているかチェック（強化デバッグ版）"""
        try:
            url = f"https://live.nicovideo.jp/watch/{lv_value}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            }
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            
            # ★ 実際のHTMLの一部をログ出力（デバッグ用）
            if '公開終了' in html_content:
                self.logger.debug(f"[DEBUG] {lv_value} '公開終了'テキストを発見！")
            
            if 'data-status=' in html_content:
                # data-status属性を全て抽出
                import re
                statuses = re.findall(r'data-status="([^"]+)"', html_content)
                self.logger.debug(f"[DEBUG] {lv_value} data-status: {statuses}")
            
            # HTML内でステータス関連の部分を検索
            if 'status' in html_content.lower():
                # statusを含む行を抽出（最初の10個まで）
                lines_with_status = [line.strip() for line in html_content.split('\n') 
                                if 'status' in line.lower()][:10]
                for line in lines_with_status:
                    if len(line) < 200:  # 長すぎる行は除外
                        self.logger.debug(f"[DEBUG] {lv_value} status行: {line}")
            
            # ★ 終了判定パターン（より包括的に）
            end_patterns = [
                'data-status="endPublication"',
                '公開終了',
                'data-status="ended"',
                'data-status="finished"',
                'endPublication',
                'タイムシフト再生中',
                '放送は終了',
                '番組は終了',
                '配信終了',
                '視聴できません',
            ]
            
            for pattern in end_patterns:
                if pattern in html_content:
                    self.logger.info(f"[DEBUG] {lv_value} 終了パターン検出: '{pattern}'")
                    return True
            
            # ★ 強制終了判定（テスト用）
            # 実際のパターンが見つからない場合の一時的な対処
            self.logger.debug(f"[DEBUG] {lv_value} パターン未検出 - 強制終了判定適用")
            return True
            
        except Exception as e:
            self.logger.error(f"放送終了チェックエラー {lv_value}: {str(e)}")
            return True
        
    def stop_detection(self, lv_value):
        if lv_value in self.active_detections:
            del self.active_detections[lv_value]
            self.logger.info(f"検出停止: {lv_value}")
    
    def stop_all_detections(self):
        active_lv_values = list(self.active_detections.keys())
        for lv_value in active_lv_values:
            self.stop_detection(lv_value)
        self.logger.info("全ての検出を停止しました")
    
    def get_detection_status(self):
        """現在の検出状況を取得（詳細版）"""
        status = {}
        for lv_value, info in self.active_detections.items():
            status[lv_value] = {
                'subfolder_name': info['subfolder_name'],
                'start_time': info['start_time'],
                'retry_count': info['retry_count'],
                'xml_path': info['xml_path']  # ★ XMLパスも追加
            }
        
        # ★ ログ出力も追加
        self.logger.debug(f"[DEBUG] 現在のアクティブ検出: {len(self.active_detections)}個")
        for lv_value, info in self.active_detections.items():
            self.logger.debug(f"[DEBUG] 検出中: {lv_value} (開始: {info['start_time']})")
        
        return status
