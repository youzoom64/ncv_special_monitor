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
            {"user_id": "12345678", "display_name": "繝繧ｹ繝医Θ繝ｼ繧ｶ繝ｼ1"},
            {"user_id": "87654321", "display_name": "繝繧ｹ繝医Θ繝ｼ繧ｶ繝ｼ2"},
            {"user_id": "11111111", "display_name": "驟堺ｿ｡蟶ｸ騾｣縺輔ｓ"},
            {"user_id": "22222222", "display_name": "髱｢逋ｽ繧ｳ繝｡繝ｳ繝郁ｷ莠ｺ"}
        ]
        
    def setup_directories(self):
        """蠢隕√↑繝繧｣繝ｬ繧ｯ繝医Μ繧剃ｽ懈"""
        directories = [
            "test_output/SpecialUser",
            "test_output/templates",
            "test_output/templates/css",
            "test_output/templates/js"
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def generate_test_broadcast_data(self):
        """繝繧ｹ繝育畑縺ｮ謾ｾ騾√ョ繝ｼ繧ｿ繧堤函謌"""
        now = datetime.now()
        start_time = int((now - timedelta(hours=2)).timestamp())
        end_time = int(now.timestamp())
        
        return {
            "lv_value": "lv123456789",
            "subfolder_name": "test_broadcast",
            "live_title": "縲舌ユ繧ｹ繝磯堺ｿ｡縲践TML繧ｸ繧ｧ繝阪Ξ繝ｼ繧ｿ繝ｼ縺ｮ繝繧ｹ繝",
            "broadcaster": "繝繧ｹ繝磯堺ｿ｡閠",
            "community_name": "繝繧ｹ繝医さ繝溘Η繝九ユ繧｣",
            "start_time": str(start_time),
            "end_time": str(end_time),
            "watch_count": "150",
            "comment_count": "300",
            "owner_id": "99999999",
            "owner_name": "繝繧ｹ繝磯堺ｿ｡閠"
        }
    
    def generate_test_comments(self, user_id, user_name, count=10):
        """繝繧ｹ繝育畑縺ｮ繧ｳ繝｡繝ｳ繝医ョ繝ｼ繧ｿ繧堤函謌"""
        comments = []
        base_time = int(datetime.now().timestamp()) - 7200  # 2譎る俣蜑阪°繧蛾幕蟋
        
        sample_comments = [
            "縺薙ｓ縺ｫ縺｡縺ｯ縲",
            "髱｢逋ｽ縺驟堺ｿ｡縺ｧ縺吶ｭｼ",
            "ww",
            "88888888",
            "莉頑律繧る堺ｿ｡縺顔夢繧梧ｧ倥〒縺",
            "髻ｳ螢ｰ閨槭％縺医※縺ｾ縺吶ｈ縲",
            "逕ｻ雉ｪ縺阪ｌ縺縺ｧ縺吶ｭ",
            "縺ｾ縺溯ｦ九↓譚･縺ｾ縺呻ｼ",
            "縺ゅｊ縺後→縺縺斐＊縺縺ｾ縺励◆",
            "谺｡縺ｮ驟堺ｿ｡繧よ･ｽ縺励∩縺ｧ縺"
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
        """繝繧ｹ繝育畑縺ｮAI蛻譫千ｵ先棡繧堤函謌"""
        analysis_templates = [
            f"""
            <div style="background-color: #f0f8ff; padding: 10px; margin: 10px 0; border-left: 4px solid #0066cc;">
            <strong>AI蛻譫先ュ蝣ｱ</strong><br>
            蛻譫舌Δ繝繝ｫ: 繝繧ｹ繝育畑AI<br>
            繝励Ο繝ｳ繝励ヨ: 繝繝輔か繝ｫ繝医励Ο繝ｳ繝励ヨ<br>
            蛻譫先律譎: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            蛻譫仙ｯｾ雎｡: {comment_count}莉ｶ縺ｮ繧ｳ繝｡繝ｳ繝
            </div>
            
            <strong>繝ｦ繝ｼ繧ｶ繝ｼ蛻譫千ｵ先棡</strong><br><br>
            
            <strong>縲須user_name}縺輔ｓ縺ｮ迚ｹ蠕ｴ縲</strong><br>
            縺薙ｮ繝ｦ繝ｼ繧ｶ繝ｼ縺ｯ驟堺ｿ｡縺ｫ蟇ｾ縺励※髱槫ｸｸ縺ｫ遨肴･ｵ逧縺ｫ蜿ょ刈縺輔ｌ繧区婿縺ｧ縺吶<br>
            繧ｳ繝｡繝ｳ繝医ｮ謚慕ｨｿ鬆ｻ蠎ｦ縺碁ｫ倥￥縲驟堺ｿ｡閠縺ｨ縺ｮ濶ｯ螂ｽ縺ｪ髢｢菫よｧ縺御ｼｺ縺医∪縺吶<br><br>
            
            <strong>縲舌さ繝｡繝ｳ繝亥だ蜷代</strong><br>
            - 謖ｨ諡ｶ繧諢溯ｬ昴ｮ繧ｳ繝｡繝ｳ繝医′螟壹＞<br>
            - 驟堺ｿ｡縺ｮ謚陦鍋噪縺ｪ髱｢縺ｫ縺､縺縺ｦ繧りｨ蜿<br>
            - 繝昴ず繝繧｣繝悶↑逋ｺ險縺檎岼遶九▽<br><br>
            
            <strong>縲宣堺ｿ｡縺ｸ縺ｮ雋｢迪ｮ蠎ｦ縲</strong><br>
            鬮倥＞雋｢迪ｮ蠎ｦ繧堤､ｺ縺励※縺翫ｊ縲驟堺ｿ｡縺ｮ逶帙ｊ荳翫£縺ｫ驥崎ｦ√↑蠖ｹ蜑ｲ繧呈棡縺溘＠縺ｦ縺縺ｾ縺吶<br>
            莉悶ｮ隕冶ｴ閠縺ｸ縺ｮ蠖ｱ髻ｿ繧り憶螂ｽ縺ｧ縲√さ繝溘Η繝九ユ繧｣縺ｮ豢ｻ諤ｧ蛹悶↓蟇荳弱＠縺ｦ縺縺ｾ縺吶<br><br>
            
            <strong>縲先耳螂ｨ蟇ｾ蠢懊</strong><br>
            邯咏ｶ夂噪縺ｪ髢｢菫らｶｭ謖√ｒ謗ｨ螂ｨ縺励∪縺吶ら音蛻･縺ｪ驟堺ｿ｡莨∫判縺ｸ縺ｮ諡帛ｾ縺ｪ縺ｩ繧よ､懆ｨ弱〒縺阪ｋ縺ｧ縺励ｇ縺縲
            """,
            
            f"""
            <div style="background-color: #f0f8ff; padding: 10px; margin: 10px 0; border-left: 4px solid #0066cc;">
            <strong>AI蛻譫先ュ蝣ｱ</strong><br>
            蛻譫舌Δ繝繝ｫ: 繝繧ｹ繝育畑AI<br>
            繝励Ο繝ｳ繝励ヨ: 蛟句挨繝励Ο繝ｳ繝励ヨ<br>
            蛻譫先律譎: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            蛻譫仙ｯｾ雎｡: {comment_count}莉ｶ縺ｮ繧ｳ繝｡繝ｳ繝
            </div>
            
            <strong>隧ｳ邏ｰ繝ｦ繝ｼ繧ｶ繝ｼ蛻譫</strong><br><br>
            
            <strong>縲占｡悟虚繝代ち繝ｼ繝ｳ蛻譫舌</strong><br>
            {user_name}縺輔ｓ縺ｯ驟堺ｿ｡髢句ｧ九°繧臥ｵゆｺ縺ｾ縺ｧ荳雋ｫ縺励※蜿ょ刈縺輔ｌ繧玖ｦ冶ｴ閠縺ｧ縺吶<br>
            繧ｳ繝｡繝ｳ繝医ｮ繧ｿ繧､繝溘Φ繧ｰ縺碁←蛻縺ｧ縲驟堺ｿ｡縺ｮ豬√ｌ繧堤炊隗｣縺励※縺繧区ｧ伜ｭ舌′莨ｺ縺医∪縺吶<br><br>
            
            <strong>縲舌さ繝溘Η繝九ユ繧｣蜀縺ｧ縺ｮ遶九■菴咲ｽｮ縲</strong><br>
            - 蜿､蜿りｦ冶ｴ閠縺ｨ縺励※縺ｮ螳牙ｮ壽─<br>
            - 譁ｰ隕剰ｦ冶ｴ閠縺ｸ縺ｮ繝輔か繝ｭ繝ｼ<br>
            - 驟堺ｿ｡閠縺ｸ縺ｮ繧ｵ繝昴ｼ繝亥ｧｿ蜍｢<br><br>
            
            <strong>縲千音險倅ｺ矩縲</strong><br>
            縺薙ｮ繝ｦ繝ｼ繧ｶ繝ｼ縺ｮ蟄伜惠縺ｯ驟堺ｿ｡縺ｮ螳牙ｮ壽ｧ縺ｫ螟ｧ縺阪￥蟇荳弱＠縺ｦ縺縺ｾ縺吶<br>
            邯咏ｶ夂噪縺ｪ隕冶ｴ縺ｨ驕ｩ蛻縺ｪ繧ｳ繝｡繝ｳ繝医↓繧医ｊ縲驟堺ｿ｡縺ｮ蜩∬ｳｪ蜷台ｸ翫↓雋｢迪ｮ縺励※縺縺ｾ縺吶
            """
        ]
        
        return random.choice(analysis_templates)
    
    def copy_template_files(self):
        """繝繝ｳ繝励Ξ繝ｼ繝医ヵ繧｡繧､繝ｫ繧偵さ繝斐ｼ"""
        # 譌｢蟄倥ｮ繝繝ｳ繝励Ξ繝ｼ繝医ヵ繧｡繧､繝ｫ繧偵さ繝斐ｼ
        template_files = [
            ("templates/css/archive-style.css", "test_output/templates/css/main.css"),
            ("templates/js/archive-player.js", "test_output/templates/js/main.js")
        ]
        
        for src, dst in template_files:
            if os.path.exists(src):
                shutil.copy2(src, dst)
    
    def create_user_detail_template(self):
        """繝ｦ繝ｼ繧ｶ繝ｼ隧ｳ邏ｰ繝壹ｼ繧ｸ縺ｮ繝繝ｳ繝励Ξ繝ｼ繝医ｒ菴懈"""
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
                    <span class="stat-label">髢句ｧ区凾髢</span>
                    <span class="stat-value">{{start_time}}</span>
                </div>
            </div>
        </div>
    </div>

    <section class="user-profile">
        <div class="section-title">
            <span class="title-icon">敎､</span>
            繝ｦ繝ｼ繧ｶ繝ｼ諠蝣ｱ
        </div>
        <div class="chat-container">
            <div class="chat-message">
                <div class="message-avatar">
                    <img src="{{user_avatar}}" alt="{{user_name}}縺ｮ繧｢繝舌ち繝ｼ" onerror="this.src='https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/defaults/blank.jpg'">
                    <span class="avatar-name">{{user_name}}</span>
                </div>
                <div class="message-bubble">
                    <strong>繝ｦ繝ｼ繧ｶ繝ｼID:</strong> {{user_id}}<br>
                    <strong>繝励Ο繝輔ぅ繝ｼ繝ｫ:</strong> <a href="{{user_profile_url}}" target="_blank">繝九さ繝九さ蜍慕判縺ｧ隕九ｋ</a>
                </div>
            </div>
        </div>
    </section>

    <section class="comments-section">
        <div class="section-title">
            <span class="title-icon">昀ｬ</span>
            繧ｳ繝｡繝ｳ繝亥ｱ･豁ｴ
        </div>
        <div class="chat-container">
            <table border="1" style="width: 100%; color: red; text-shadow: 2px 2px 2px rgba(110, 110, 110, 0.5);">
                <thead>
                    <tr>
                        <th style="padding: 8px;">No</th>
                        <th style="padding: 8px;">驟堺ｿ｡蜀譎る俣</th>
                        <th style="padding: 8px;">譌･譎</th>
                        <th style="padding: 8px;">繧ｳ繝｡繝ｳ繝亥螳ｹ</th>
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
            <span class="title-icon">昻</span>
            AI蛻譫千ｵ先棡
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
        """繝ｦ繝ｼ繧ｶ繝ｼ荳隕ｧ繝壹ｼ繧ｸ縺ｮ繝繝ｳ繝励Ξ繝ｼ繝医ｒ菴懈"""
        template_content = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{broadcaster_name}} - 驟堺ｿ｡荳隕ｧ</title>
    <link rel="stylesheet" href="css/main.css">
</head>
<body>
    <div class="broadcast-header">
        <div class="header-content">
            <h1 class="broadcast-title">{{broadcaster_name}}縺ｮ驟堺ｿ｡螻･豁ｴ</h1>
        </div>
    </div>

    <section class="broadcast-list">
        <div class="section-title">
            <span class="title-icon">昕ｺ</span>
            驟堺ｿ｡荳隕ｧ
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
        """UNIX譎る俣繧呈律譎り｡ｨ險倥↓螟画鋤"""
        try:
            unix_time = int(unix_time_str)
            dt = datetime.fromtimestamp(unix_time)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return str(unix_time_str)
    
    def format_elapsed_time(self, seconds):
        """邨碁℃遘呈焚繧呈凾:蛻:遘貞ｽ｢蠑上↓螟画鋤"""
        try:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except:
            return "00:00:00"
    
    def get_user_icon_path(self, user_id):
        """繝九さ繝九さ蜍慕判縺ｮ繝ｦ繝ｼ繧ｶ繝ｼ繧｢繧､繧ｳ繝ｳ繝代せ繧堤函謌"""
        if len(user_id) <= 4:
            return f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{user_id}.jpg"
        else:
            path_prefix = user_id[:-4]
            return f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{path_prefix}/{user_id}.jpg"
    
    def escape_html(self, text):
        """HTML繧ｨ繧ｹ繧ｱ繝ｼ繝"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
    
    def generate_comment_rows(self, comments, start_time_str):
        """繧ｳ繝｡繝ｳ繝医ユ繝ｼ繝悶Ν縺ｮ陦後ｒ逕滓"""
        rows = []
        
        try:
            start_time = int(start_time_str) if start_time_str else 0
        except:
            start_time = 0
        
        for i, comment in enumerate(comments, 1):
            comment_timestamp = comment.get('date', 0)
            date_str = self.format_unix_time(comment_timestamp)
            
            # 驟堺ｿ｡蜀譎る俣繧定ｨ育ｮ
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
        """繝繧ｹ繝育畑HTML繝壹ｼ繧ｸ繧堤函謌"""
        print("繝繧ｹ繝育畑HTML繝壹ｼ繧ｸ逕滓舌ｒ髢句ｧ...")
        
        # 繝繝ｳ繝励Ξ繝ｼ繝医ヵ繧｡繧､繝ｫ繧剃ｽ懈
        self.copy_template_files()
        self.create_user_detail_template()
        self.create_user_list_template()
        
        # 謾ｾ騾√ョ繝ｼ繧ｿ繧堤函謌
        broadcast_info = self.generate_test_broadcast_data()
        
        # 蜷繝ｦ繝ｼ繧ｶ繝ｼ縺ｮHTML繧堤函謌
        for user_data in self.sample_users:
            user_id = user_data["user_id"]
            user_name = user_data["display_name"]
            
            print(f"繝ｦ繝ｼ繧ｶ繝ｼ {user_name} 縺ｮ HTML 繧堤函謌蝉ｸｭ...")
            
            # 繧ｳ繝｡繝ｳ繝医ョ繝ｼ繧ｿ繧堤函謌
            comments = self.generate_test_comments(user_id, user_name, random.randint(5, 15))
            
            # AI蛻譫舌ｒ逕滓
            ai_analysis = self.generate_ai_analysis(user_name, len(comments))
            
            # 繝ｦ繝ｼ繧ｶ繝ｼ繝繧｣繝ｬ繧ｯ繝医Μ繧剃ｽ懈
            user_dir = f"test_output/SpecialUser/{user_id}_{user_name}"
            os.makedirs(user_dir, exist_ok=True)
            
            # CSS縺ｨJS繧偵さ繝斐ｼ
            os.makedirs(f"{user_dir}/css", exist_ok=True)
            os.makedirs(f"{user_dir}/js", exist_ok=True)
            
            if os.path.exists("test_output/templates/css/main.css"):
                shutil.copy2("test_output/templates/css/main.css", f"{user_dir}/css/main.css")
            if os.path.exists("test_output/templates/js/main.js"):
                shutil.copy2("test_output/templates/js/main.js", f"{user_dir}/js/main.js")
            
            # 隧ｳ邏ｰ繝壹ｼ繧ｸHTML繧堤函謌
            self.generate_detail_page(user_data, comments, broadcast_info, ai_analysis, user_dir)
            
            # 荳隕ｧ繝壹ｼ繧ｸHTML繧堤函謌
            self.generate_list_page(user_data, comments, broadcast_info, user_dir)
            
            # JSON繝輔ぃ繧､繝ｫ繧堤函謌
            self.save_json_files(user_data, comments, broadcast_info, user_dir)
            
            print(f"繝ｦ繝ｼ繧ｶ繝ｼ {user_name} 縺ｮ HTML 逕滓仙ｮ御ｺ")
        
        print("蜈ｨ縺ｦ縺ｮ繝繧ｹ繝育畑HTML繝壹ｼ繧ｸ縺ｮ逕滓舌′螳御ｺ縺励∪縺励◆ｼ")
        print("逕滓舌＆繧後◆繝輔ぃ繧､繝ｫ縺ｯ test_output 繝繧｣繝ｬ繧ｯ繝医Μ縺ｫ縺ゅｊ縺ｾ縺吶")
    
    def generate_detail_page(self, user_data, comments, broadcast_info, ai_analysis, user_dir):
        """隧ｳ邏ｰ繝壹ｼ繧ｸ繧堤函謌"""
        with open("test_output/templates/user_detail.html", "r", encoding="utf-8") as f:
            template = f.read()
        
        # 繧ｳ繝｡繝ｳ繝郁｡後ｒ逕滓
        comment_rows = self.generate_comment_rows(comments, broadcast_info.get('start_time', ''))
        
        # 繝繝ｳ繝励Ξ繝ｼ繝亥､画焚繧堤ｽｮ謠
        html_content = template.replace('{{broadcast_title}}', broadcast_info.get('live_title', '繧ｿ繧､繝医Ν荳肴'))
        html_content = html_content.replace('{{start_time}}', self.format_unix_time(broadcast_info.get('start_time', '')))
        html_content = html_content.replace('{{user_avatar}}', self.get_user_icon_path(user_data['user_id']))
        html_content = html_content.replace('{{user_name}}', user_data['display_name'])
        html_content = html_content.r
