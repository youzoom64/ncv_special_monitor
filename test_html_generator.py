# test_html_generator.py
import os
import json
import shutil
from datetime import datetime, timedelta
import random

class TestHTMLGenerator:
    def __init__(self):
        self.setup_directories()
        self.sample_users = [
            {"user_id": "12345678", "display_name": "テストユーザー1"},
            {"user_id": "87654321", "display_name": "テストユーザー2"},
            {"user_id": "11111111", "display_name": "配信常連さん"},
            {"user_id": "22222222", "display_name": "面白コメント職人"}
        ]
        
    def setup_directories(self):
        """必要なディレクトリを作成"""
        directories = [
            "test_output/SpecialUser",
            "test_output/templates",
            "test_output/templates/css",
            "test_output/templates/js"
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def generate_test_broadcast_data(self):
        """テスト用の放送データを生成"""
        now = datetime.now()
        start_time = int((now - timedelta(hours=2)).timestamp())
        end_time = int(now.timestamp())
        
        return {
            "lv_value": "lv123456789",
            "subfolder_name": "test_broadcast",
            "live_title": "【テスト配信】HTMLジェネレーターのテスト",
            "broadcaster": "テスト配信者",
            "community_name": "テストコミュニティ",
            "start_time": str(start_time),
            "end_time": str(end_time),
            "watch_count": "150",
            "comment_count": "300",
            "owner_id": "99999999",
            "owner_name": "テスト配信者"
        }
    
    def generate_test_comments(self, user_id, user_name, count=10):
        """テスト用のコメントデータを生成"""
        comments = []
        base_time = int(datetime.now().timestamp()) - 7200  # 2時間前から開始
        
        sample_comments = [
            "こんにちは〜",
            "面白い配信ですね！",
            "ww",
            "88888888",
            "今日も配信お疲れ様です",
            "音声聞こえてますよ〜",
            "画質きれいですね",
            "また見に来ます！",
            "ありがとうございました",
            "次の配信も楽しみです"
        ]
        
        for i in range(count):
            comment_time = base_time + (i * 60) + random.randint(0, 59)
            comments.append({
                "no": i + 1,
                "user_id": user_id,
                "user_name": user_name,
                "text": random.choice(sample_comments),
                "date": comment_time,
                "premium": random.randint(0, 1),
                "anonymity": False
            })
        
        return comments
    
    def generate_ai_analysis(self, user_name, comment_count):
        """テスト用のAI分析結果を生成"""
        analysis_templates = [
            f"""
            <div style="background-color: #f0f8ff; padding: 10px; margin: 10px 0; border-left: 4px solid #0066cc;">
            <strong>AI分析情報</strong><br>
            分析モデル: テスト用AI<br>
            プロンプト: デフォルトプロンプト<br>
            分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            分析対象: {comment_count}件のコメント
            </div>
            
            <strong>ユーザー分析結果</strong><br><br>
            
            <strong>【{user_name}さんの特徴】</strong><br>
            このユーザーは配信に対して非常に積極的に参加される方です。<br>
            コメントの投稿頻度が高く、配信者との良好な関係性が伺えます。<br><br>
            
            <strong>【コメント傾向】</strong><br>
            - 挨拶や感謝のコメントが多い<br>
            - 配信の技術的な面についても言及<br>
            - ポジティブな発言が目立つ<br><br>
            
            <strong>【配信への貢献度】</strong><br>
            高い貢献度を示しており、配信の盛り上げに重要な役割を果たしています。<br>
            他の視聴者への影響も良好で、コミュニティの活性化に寄与しています。<br><br>
            
            <strong>【推奨対応】</strong><br>
            継続的な関係維持を推奨します。特別な配信企画への招待なども検討できるでしょう。
            """,
            
            f"""
            <div style="background-color: #f0f8ff; padding: 10px; margin: 10px 0; border-left: 4px solid #0066cc;">
            <strong>AI分析情報</strong><br>
            分析モデル: テスト用AI<br>
            プロンプト: 個別プロンプト<br>
            分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            分析対象: {comment_count}件のコメント
            </div>
            
            <strong>詳細ユーザー分析</strong><br><br>
            
            <strong>【行動パターン分析】</strong><br>
            {user_name}さんは配信開始から終了まで一貫して参加される視聴者です。<br>
            コメントのタイミングが適切で、配信の流れを理解している様子が伺えます。<br><br>
            
            <strong>【コミュニティ内での立ち位置】</strong><br>
            - 古参視聴者としての安定感<br>
            - 新規視聴者へのフォロー<br>
            - 配信者へのサポート姿勢<br><br>
            
            <strong>【特記事項】</strong><br>
            このユーザーの存在は配信の安定性に大きく寄与しています。<br>
            継続的な視聴と適切なコメントにより、配信の品質向上に貢献しています。
            """
        ]
        
        return random.choice(analysis_templates)
    
    def copy_template_files(self):
        """テンプレートファイルをコピー"""
        # 既存のテンプレートファイルをコピー
        template_files = [
            ("templates/css/archive-style.css", "test_output/templates/css/main.css"),
            ("templates/js/archive-player.js", "test_output/templates/js/main.js")
        ]
        
        for src, dst in template_files:
            if os.path.exists(src):
                shutil.copy2(src, dst)
    
    def create_user_detail_template(self):
        """ユーザー詳細ページのテンプレートを作成"""
        template_content = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{user_name}} - {{broadcast_title}}</title>
    <link rel="stylesheet" href="css/main.css">
</head>
<body>
    <div class="broadcast-header">
        <div class="header-content">
            <h1 class="broadcast-title">{{broadcast_title}}</h1>
            <div class="broadcast-stats">
                <div class="stat-item">
                    <span class="stat-label">開始時間</span>
                    <span class="stat-value">{{start_time}}</span>
                </div>
            </div>
        </div>
    </div>

    <section class="user-profile">
        <div class="section-title">
            <span class="title-icon">👤</span>
            ユーザー情報
        </div>
        <div class="chat-container">
            <div class="chat-message">
                <div class="message-avatar">
                    <img src="{{user_avatar}}" alt="{{user_name}}のアバター" onerror="this.src='https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/defaults/blank.jpg'">
                    <span class="avatar-name">{{user_name}}</span>
                </div>
                <div class="message-bubble">
                    <strong>ユーザーID:</strong> {{user_id}}<br>
                    <strong>プロフィール:</strong> <a href="{{user_profile_url}}" target="_blank">ニコニコ動画で見る</a>
                </div>
            </div>
        </div>
    </section>

    <section class="comments-section">
        <div class="section-title">
            <span class="title-icon">💬</span>
            コメント履歴
        </div>
        <div class="chat-container">
            <table border="1" style="width: 100%; color: red; text-shadow: 2px 2px 2px rgba(110, 110, 110, 0.5);">
                <thead>
                    <tr>
                        <th style="padding: 8px;">No</th>
                        <th style="padding: 8px;">配信内時間</th>
                        <th style="padding: 8px;">日時</th>
                        <th style="padding: 8px;">コメント内容</th>
                    </tr>
                </thead>
                <tbody>
                    {{comment_rows}}
                </tbody>
            </table>
        </div>
    </section>

    <section class="analysis-section">
        <div class="section-title">
            <span class="title-icon">🤖</span>
            AI分析結果
        </div>
        <div class="chat-container">
            {{analysis_text}}
        </div>
    </section>

    <script src="js/main.js"></script>
</body>
</html>"""

        with open("test_output/templates/user_detail.html", "w", encoding="utf-8") as f:
            f.write(template_content)
    
    def create_user_list_template(self):
        """ユーザー一覧ページのテンプレートを作成"""
        template_content = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{broadcaster_name}} - 配信一覧</title>
    <link rel="stylesheet" href="css/main.css">
</head>
<body>
    <div class="broadcast-header">
        <div class="header-content">
            <h1 class="broadcast-title">{{broadcaster_name}}の配信履歴</h1>
        </div>
    </div>

    <section class="broadcast-list">
        <div class="section-title">
            <span class="title-icon">📋</span>
            配信一覧
        </div>
        {{broadcast_items}}
    </section>

    <script>
        function toggleDiv(id) {
            const element = document.getElementById(id);
            if (element.style.display === 'none') {
                element.style.display = 'block';
            } else {
                element.style.display = 'none';
            }
        }
    </script>
</body>
</html>"""

        with open("test_output/templates/user_list.html", "w", encoding="utf-8") as f:
            f.write(template_content)
    
    def format_unix_time(self, unix_time_str):
        """UNIX時間を日時表記に変換"""
        try:
            unix_time = int(unix_time_str)
            dt = datetime.fromtimestamp(unix_time)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return str(unix_time_str)
    
    def format_elapsed_time(self, seconds):
        """経過秒数を時:分:秒形式に変換"""
        try:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except:
            return "00:00:00"
    
    def get_user_icon_path(self, user_id):
        """ニコニコ動画のユーザーアイコンパスを生成"""
        if len(user_id) <= 4:
            return f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{user_id}.jpg"
        else:
            path_prefix = user_id[:-4]
            return f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{path_prefix}/{user_id}.jpg"
    
    def escape_html(self, text):
        """HTMLエスケープ"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
    
    def generate_comment_rows(self, comments, start_time_str):
        """コメントテーブルの行を生成"""
        rows = []
        
        try:
            start_time = int(start_time_str) if start_time_str else 0
        except:
            start_time = 0
        
        for i, comment in enumerate(comments, 1):
            comment_timestamp = comment.get('date', 0)
            date_str = self.format_unix_time(comment_timestamp)
            
            # 配信内時間を計算
            if start_time and comment_timestamp:
                try:
                    elapsed_seconds = int(comment_timestamp) - start_time
                    elapsed_time = self.format_elapsed_time(elapsed_seconds)
                except:
                    elapsed_time = "00:00:00"
            else:
                elapsed_time = "00:00:00"
            
            row = f'''
            <tr>
                <td style="padding: 5px;">{i}</td>
                <td style="padding: 5px;">{elapsed_time}</td>
                <td style="padding: 5px;">{date_str}</td>
                <td style="padding: 5px;"><b style="font-size: 20px;">{self.escape_html(comment.get('text', ''))}</b></td>
            </tr>'''
            rows.append(row)
        
        return '\n'.join(rows)
    
    def create_test_html_pages(self):
        """テスト用HTMLページを生成"""
        print("テスト用HTMLページ生成を開始...")
        
        # テンプレートファイルを作成
        self.copy_template_files()
        self.create_user_detail_template()
        self.create_user_list_template()
        
        # 放送データを生成
        broadcast_info = self.generate_test_broadcast_data()
        
        # 各ユーザーのHTMLを生成
        for user_data in self.sample_users:
            user_id = user_data["user_id"]
            user_name = user_data["display_name"]
            
            print(f"ユーザー {user_name} の HTML を生成中...")
            
            # コメントデータを生成
            comments = self.generate_test_comments(user_id, user_name, random.randint(5, 15))
            
            # AI分析を生成
            ai_analysis = self.generate_ai_analysis(user_name, len(comments))
            
            # ユーザーディレクトリを作成
            user_dir = f"test_output/SpecialUser/{user_id}_{user_name}"
            os.makedirs(user_dir, exist_ok=True)
            
            # CSSとJSをコピー
            os.makedirs(f"{user_dir}/css", exist_ok=True)
            os.makedirs(f"{user_dir}/js", exist_ok=True)
            
            if os.path.exists("test_output/templates/css/main.css"):
                shutil.copy2("test_output/templates/css/main.css", f"{user_dir}/css/main.css")
            if os.path.exists("test_output/templates/js/main.js"):
                shutil.copy2("test_output/templates/js/main.js", f"{user_dir}/js/main.js")
            
            # 詳細ページHTMLを生成
            self.generate_detail_page(user_data, comments, broadcast_info, ai_analysis, user_dir)
            
            # 一覧ページHTMLを生成
            self.generate_list_page(user_data, comments, broadcast_info, user_dir)
            
            # JSONファイルを生成
            self.save_json_files(user_data, comments, broadcast_info, user_dir)
            
            print(f"ユーザー {user_name} の HTML 生成完了")
        
        print("全てのテスト用HTMLページの生成が完了しました！")
        print("生成されたファイルは test_output ディレクトリにあります。")
    
    def generate_detail_page(self, user_data, comments, broadcast_info, ai_analysis, user_dir):
        """詳細ページを生成"""
        with open("test_output/templates/user_detail.html", "r", encoding="utf-8") as f:
            template = f.read()
        
        # コメント行を生成
        comment_rows = self.generate_comment_rows(comments, broadcast_info.get('start_time', ''))
        
        # テンプレート変数を置換
        html_content = template.replace('{{broadcast_title}}', broadcast_info.get('live_title', 'タイトル不明'))
        html_content = html_content.replace('{{start_time}}', self.format_unix_time(broadcast_info.get('start_time', '')))
        html_content = html_content.replace('{{user_avatar}}', self.get_user_icon_path(user_data['user_id']))
        html_content = html_content.replace('{{user_name}}', user_data['display_name'])
        html_content = html_content.replace('{{user_id}}', user_data['user_id'])
        html_content = html_content.replace('{{user_profile_url}}', f"https://www.nicovideo.jp/user/{user_data['user_id']}")
        html_content = html_content.replace('{{comment_rows}}', comment_rows)
        html_content = html_content.replace('{{analysis_text}}', ai_analysis)
        
        # HTMLファイルを保存
        with open(f"{user_dir}/detail.html", "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def generate_list_page(self, user_data, comments, broadcast_info, user_dir):
        """一覧ページを生成"""
        with open("test_output/templates/user_list.html", "r", encoding="utf-8") as f:
            template = f.read()
        
        # 放送アイテムを生成
        broadcast_items = f"""
        <div class="broadcast-item">
            <h3>{broadcast_info.get('live_title', 'タイトル不明')}</h3>
            <p>開始時間: {self.format_unix_time(broadcast_info.get('start_time', ''))}</p>
            <p>コメント数: {len(comments)}件</p>
            <a href="detail.html">詳細を見る</a>
        </div>
        """
        
        # テンプレート変数を置換
        html_content = template.replace('{{broadcaster_name}}', user_data['display_name'])
        html_content = html_content.replace('{{broadcast_items}}', broadcast_items)
        
        # HTMLファイルを保存
        with open(f"{user_dir}/index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def save_json_files(self, user_data, comments, broadcast_info, user_dir):
        """JSONファイルを保存"""
        # コメントデータを保存
        with open(f"{user_dir}/comments.json", "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        
        # 放送データを保存
        with open(f"{user_dir}/broadcast_data.json", "w", encoding="utf-8") as f:
            json.dump(broadcast_info, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    generator = TestHTMLGenerator()
    generator.create_test_html_pages()
