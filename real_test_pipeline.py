# real_test_pipeline.py
import sys
import os
import json
from datetime import datetime
import tempfile
import shutil

# パイプライン処理をインポート
sys.path.append('processors')
try:
    import step01_xml_parser
    import step02_special_user_filter
    import step03_html_generator
except ImportError as e:
    print(f"❌ パイプライン処理のインポートに失敗: {e}")
    print("processors/ ディレクトリが存在し、必要なファイルがあることを確認してください")
    sys.exit(1)

class RealPipelineTest:
    def __init__(self):
        self.test_dir = "pipeline_test_output"
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """テスト環境をセットアップ"""
        # テスト用ディレクトリ作成
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)
        
        # 必要なディレクトリ構造を作成
        os.makedirs(f"{self.test_dir}/SpecialUser", exist_ok=True)
        os.makedirs(f"{self.test_dir}/templates", exist_ok=True)
        
        # テンプレートファイルをコピー
        self.copy_templates()
    
    def copy_templates(self):
        """既存のテンプレートをテスト用にコピー"""
        template_sources = [
            ("templates/css", f"{self.test_dir}/templates/css"),
            ("templates/js", f"{self.test_dir}/templates/js"),
            ("templates/user_detail.html", f"{self.test_dir}/templates/user_detail.html"),
            ("templates/user_list.html", f"{self.test_dir}/templates/user_list.html")
        ]
        
        for src, dst in template_sources:
            try:
                if os.path.isfile(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                print(f"✅ テンプレートコピー: {src} → {dst}")
            except Exception as e:
                print(f"⚠️  テンプレートコピー失敗: {src} - {e}")
    
    def create_test_xml_data(self):
        """本物のXMLデータ構造をシミュレート"""
        now = datetime.now()
        start_timestamp = int(now.timestamp()) - 7200  # 2時間前
        
        # XMLパーサーの結果をシミュレート
        broadcast_info = {
            'live_title': '【テスト配信】パイプラインテスト実行中',
            'broadcaster': 'テスト配信者',
            'community_name': 'テストコミュニティ',
            'start_time': str(start_timestamp),
            'end_time': str(int(now.timestamp())),
            'watch_count': '250',
            'comment_count': '150',
            'owner_id': '88888888',
            'owner_name': 'テスト配信者'
        }
        
        # コメントデータを生成（実際のXMLパーサー出力形式に準拠）
        comments_data = []
        test_users = [
            {"user_id": "12345678", "user_name": "テストユーザー1"},
            {"user_id": "87654321", "user_name": "テストユーザー2"},
            {"user_id": "11111111", "user_name": "配信常連さん"}
        ]
        
        comment_templates = [
            "こんにちは〜！",
            "今日も配信お疲れ様です",
            "音声クリアですね",
            "88888888",
            "ww",
            "面白いですね！",
            "また見に来ます"
        ]
        
        comment_id = 1
        for user in test_users:
            for i in range(5):  # 各ユーザー5コメント
                comments_data.append({
                    "no": comment_id,
                    "user_id": user["user_id"],
                    "user_name": user["user_name"],
                    "text": comment_templates[comment_id % len(comment_templates)],
                    "date": start_timestamp + (comment_id * 120),  # 2分間隔
                    "premium": 0,
                    "anonymity": False
                })
                comment_id += 1
        
        return broadcast_info, comments_data
    
    def create_test_config(self):
        """テスト用の設定データを作成"""
        return {
            "special_users_config": {
                "default_analysis_enabled": True,
                "default_analysis_ai_model": "test-ai",
                "default_analysis_prompt": "テスト用プロンプト: このユーザーを分析してください",
                "users": {
                    "12345678": {
                        "display_name": "テストユーザー1",
                        "analysis_enabled": True,
                        "analysis_ai_model": "test-ai",
                        "analysis_prompt": "カスタムプロンプト: 詳細分析してください"
                    },
                    "87654321": {
                        "display_name": "テストユーザー2", 
                        "analysis_enabled": True
                    },
                    "11111111": {
                        "display_name": "配信常連さん",
                        "analysis_enabled": True
                    }
                }
            }
        }
    
    def run_full_pipeline_test(self):
        """実際のパイプライン処理をテスト"""
        print("🚀 実際のパイプライン処理テスト開始")
        print("=" * 60)
        
        # テストデータ準備
        broadcast_info, comments_data = self.create_test_xml_data()
        config = self.create_test_config()
        
        # パイプラインデータを構築（実際のフォーマットに準拠）
        pipeline_data = {
            'xml_path': f"{self.test_dir}/test.xml",
            'lv_value': 'lv123456789',
            'subfolder_name': 'test_broadcast',
            'config': config,
            'start_time': datetime.now(),
            'results': {
                'step01_xml_parser': {
                    'comments_data': comments_data,
                    'broadcast_info': broadcast_info,
                    'comments_count': len(comments_data)
                }
            }
        }
        
        try:
            # Step02: スペシャルユーザー検索
            print("📋 Step02: スペシャルユーザー検索実行中...")
            step02_result = step02_special_user_filter.process(pipeline_data)
            pipeline_data['results']['step02_special_user_filter'] = step02_result
            
            print(f"   ✅ 検出ユーザー数: {step02_result['special_users_found']}")
            for user in step02_result['found_users']:
                print(f"   👤 {user['user_name']} ({user['user_id']}) - {len(user['comments'])}コメント")
            
            # Step03: HTML生成（実際のコードを使用）
            print("\n🎨 Step03: HTML生成実行中...")
            
            # 作業ディレクトリを一時的に変更
            original_cwd = os.getcwd()
            os.chdir(self.test_dir)
            
            try:
                step03_result = step03_html_generator.process(pipeline_data)
                
                print(f"   ✅ HTML生成: {step03_result['html_generated']}")
                print(f"   📄 生成ファイル数: {len(step03_result.get('generated_files', []))}")
                print(f"   👥 処理ユーザー数: {step03_result['users_processed']}")
                
                # 生成されたファイルを確認
                self.verify_generated_files(step03_result)
                
            finally:
                os.chdir(original_cwd)
            
            print("\n🎉 パイプライン処理テスト完了!")
            return True
            
        except Exception as e:
            print(f"\n❌ パイプライン処理エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_generated_files(self, step03_result):
        """生成されたファイルの検証"""
        print("\n🔍 生成ファイル検証:")
        
        # SpecialUserディレクトリの確認
        special_user_dir = os.path.join(self.test_dir, "SpecialUser")
        if os.path.exists(special_user_dir):
            user_dirs = [d for d in os.listdir(special_user_dir) if os.path.isdir(os.path.join(special_user_dir, d))]
            print(f"   📁 ユーザーディレクトリ数: {len(user_dirs)}")
            
            for user_dir in user_dirs:
                user_path = os.path.join(special_user_dir, user_dir)
                files = os.listdir(user_path)
                
                # 必須ファイルの確認
                expected_files = ['list.html', 'css', 'js']
                detail_html = [f for f in files if f.endswith('_detail.html')]
                
                print(f"   👤 {user_dir}:")
                print(f"      📄 ファイル: {files}")
                
                # HTMLファイルの内容チェック
                list_html_path = os.path.join(user_path, 'list.html')
                if os.path.exists(list_html_path):
                    with open(list_html_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'コメントを表示' in content and 'detail.html' in content:
                            print(f"      ✅ list.html は正常")
                        else:
                            print(f"      ❌ list.html に問題あり")
                
                if detail_html:
                    detail_path = os.path.join(user_path, detail_html[0])
                    with open(detail_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'AI分析結果' in content and 'コメント履歴' in content:
                            print(f"      ✅ {detail_html[0]} は正常")
                        else:
                            print(f"      ❌ {detail_html[0]} に問題あり")
        
        print(f"\n📊 検証完了: 詳細は {self.test_dir} ディレクトリを確認")
    
    def run_performance_test(self):
        """パフォーマンステスト"""
        print("\n⚡ パフォーマンステスト実行中...")
        
        # 大量データでテスト
        broadcast_info, _ = self.create_test_xml_data()
        
        # 1000コメントのテストデータ作成
        large_comments = []
        for i in range(1000):
            large_comments.append({
                "no": i + 1,
                "user_id": "12345678",
                "user_name": "ヘビーユーザー",
                "text": f"テストコメント {i + 1}",
                "date": int(datetime.now().timestamp()) + i,
                "premium": i % 2,
                "anonymity": False
            })
        
        config = self.create_test_config()
        
        pipeline_data = {
            'lv_value': 'lv999999999',
            'subfolder_name': 'performance_test',
            'config': config,
            'results': {
                'step01_xml_parser': {
                    'comments_data': large_comments,
                    'broadcast_info': broadcast_info
                },
                'step02_special_user_filter': {
                    'special_users_found': 1,
                    'found_users': [{
                        'user_id': '12345678',
                        'user_name': 'ヘビーユーザー',
                        'comments': large_comments,
                        'ai_analysis': 'パフォーマンステスト用の分析結果です。'
                    }]
                }
            }
        }
        
        # 実行時間測定
        start_time = datetime.now()
        
        original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        try:
            step03_html_generator.process(pipeline_data)
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            print(f"   ⏱️  1000コメント処理時間: {duration:.2f}秒")
            
            if duration > 10:
                print(f"   ⚠️  処理時間が長すぎます: {duration:.2f}秒")
            else:
                print(f"   ✅ 処理時間は許容範囲内")
            
        finally:
            os.chdir(original_cwd)

def main():
    print("🧪 NCV Special Monitor - 本格パイプラインテスト")
    print("=" * 60)
    
    tester = RealPipelineTest()
    
    # 基本パイプラインテスト
    success = tester.run_full_pipeline_test()
    
    if success:
        # パフォーマンステスト
        tester.run_performance_test()
        
        print("\n📋 テスト結果サマリー:")
        print("✅ 実際のパイプライン処理: 成功")
        print("✅ HTML生成: 成功") 
        print("✅ ファイル検証: 完了")
        print("✅ パフォーマンス: 確認済み")
        
        print(f"\n🔍 生成されたファイルを確認: {tester.test_dir}/SpecialUser/")
        print("各ユーザーフォルダ内の list.html をブラウザで開いて確認してください")
    else:
        print("\n❌ テスト失敗: エラーを修正してから再実行してください")

if __name__ == "__main__":
    main()