import importlib
import sys
import os
from datetime import datetime

class PipelineExecutor:
    def __init__(self, config_manager, logger, file_monitor=None):
        self.config_manager = config_manager
        self.logger = logger
        self.file_monitor = file_monitor
        
        # processorsディレクトリをパスに追加
        processors_path = os.path.join(os.path.dirname(__file__), 'processors')
        if processors_path not in sys.path:
            sys.path.append(processors_path)
            
    def execute_pipeline(self, xml_path, lv_value, subfolder_name):
        """パイプライン実行"""
        try:
            self.logger.info(f"パイプライン開始: {lv_value} ({subfolder_name})")
            
            # パイプラインデータ初期化
            config = self.config_manager.load_config()
            pipeline_data = {
                'xml_path': xml_path,
                'lv_value': lv_value,
                'subfolder_name': subfolder_name,
                'config': config,
                'start_time': datetime.now(),
                'results': {}
            }
            
            # ステップ定義
            steps = [
                'step01_xml_parser',
                'step02_special_user_filter',
                'step03_html_generator'
            ]
            
            # 各ステップを順次実行
            for step_name in steps:
                try:
                    self.logger.info(f"実行中: {step_name}")
                    
                    # ステップモジュールを動的読み込み
                    module = importlib.import_module(f"processors.{step_name}")
                    
                    # process関数を実行
                    if hasattr(module, 'process'):
                        result = module.process(pipeline_data)
                        pipeline_data['results'][step_name] = result
                        
                        # ★★★ Step01完了後に放送情報をconfigに追加 ★★★
                        if step_name == 'step01_xml_parser' and 'broadcast_info' in result:
                            pipeline_data['config']['broadcast_info'] = result['broadcast_info']
                        
                        self.logger.info(f"完了: {step_name}")
                    else:
                        self.logger.warning(f"スキップ: {step_name} (process関数なし)")
                        
                except ImportError as e:
                    self.logger.error(f"モジュール読み込みエラー: {step_name} - {str(e)}")
                    continue
                except Exception as e:
                    self.logger.error(f"ステップ実行エラー: {step_name} - {str(e)}")
                    continue
            
            # パイプライン完了
            total_time = (datetime.now() - pipeline_data['start_time']).total_seconds()
            self.logger.info(f"パイプライン完了: {lv_value} (処理時間: {total_time:.1f}秒)")
            
            # ファイルモニターに完了通知
            if self.file_monitor:
                self.file_monitor.xml_processing_completed(xml_path)
            
            return pipeline_data['results']
            
        except Exception as e:
            self.logger.error(f"パイプライン実行エラー: {lv_value} - {str(e)}")
            raise