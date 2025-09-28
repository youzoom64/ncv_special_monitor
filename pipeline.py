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
            
            # ステップ定義（Step00とStep04を追加）
            steps = [
                'step00_profile_monitor',   # ★ 新規追加
                'step01_xml_parser',
                'step02_special_user_filter',
                'step03_html_generator',
                'step04_database_storage'
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
                        
                        # ★★★ Step04完了後にDB保存結果をログ出力 ★★★
                        if step_name == 'step04_database_storage' and result.get('database_saved'):
                            self.logger.info(f"DB保存完了: 放送ID={result.get('broadcast_id')}, "
                                           f"コメント{result.get('total_comments_saved')}件, "
                                           f"AI分析{result.get('ai_analyses_saved')}件")
                    else:
                        self.logger.warning(f"スキップ: {step_name} (process関数なし)")
                        
                except ImportError as e:
                    self.logger.error(f"モジュール読み込みエラー: {step_name} - {str(e)}")
                    # Step04のエラーは致命的ではないので続行
                    if step_name != 'step04_database_storage':
                        continue
                    else:
                        self.logger.warning("データベース保存に失敗しましたが、パイプラインを続行します")
                        continue
                except Exception as e:
                    self.logger.error(f"ステップ実行エラー: {step_name} - {str(e)}")
                    # Step04のエラーは致命的ではないので続行
                    if step_name != 'step04_database_storage':
                        continue
                    else:
                        self.logger.warning("データベース保存に失敗しましたが、パイプラインを続行します")
                        continue
            
            # パイプライン完了
            total_time = (datetime.now() - pipeline_data['start_time']).total_seconds()
            self.logger.info(f"パイプライン完了: {lv_value} (処理時間: {total_time:.1f}秒)")
            
            # パイプライン結果サマリー
            summary = self._generate_pipeline_summary(pipeline_data['results'])
            self.logger.info(f"パイプライン結果: {summary}")
            
            # ファイルモニターに完了通知
            if self.file_monitor:
                self.file_monitor.xml_processing_completed(xml_path)
            
            return pipeline_data['results']
            
        except Exception as e:
            self.logger.error(f"パイプライン実行エラー: {lv_value} - {str(e)}")
            raise
    
    def _generate_pipeline_summary(self, results):
        """パイプライン実行結果のサマリーを生成"""
        summary_parts = []
        
        # Step00結果
        if 'step00_profile_monitor' in results:
            step00 = results['step00_profile_monitor']
            if step00.get('success'):
                if step00.get('profile_changed'):
                    summary_parts.append("プロフィール=変更検出")
                else:
                    summary_parts.append("プロフィール=変更なし")
            else:
                summary_parts.append("プロフィール=エラー")

        # Step01結果
        if 'step01_xml_parser' in results:
            step01 = results['step01_xml_parser']
            summary_parts.append(f"コメント解析={step01.get('comments_count', 0)}件")
        
        # Step02結果  
        if 'step02_special_user_filter' in results:
            step02 = results['step02_special_user_filter']
            summary_parts.append(f"特別ユーザー={step02.get('special_users_found', 0)}人")
        
        # Step03結果
        if 'step03_html_generator' in results:
            step03 = results['step03_html_generator']
            if step03.get('html_generated'):
                summary_parts.append(f"HTML生成={step03.get('users_processed', 0)}ユーザー")
            else:
                summary_parts.append("HTML生成=スキップ")
        
        # Step04結果
        if 'step04_database_storage' in results:
            step04 = results['step04_database_storage']
            if step04.get('database_saved'):
                summary_parts.append(f"DB保存=成功(ID:{step04.get('broadcast_id')})")
            else:
                summary_parts.append("DB保存=失敗")
        
        return ", ".join(summary_parts) if summary_parts else "結果なし"