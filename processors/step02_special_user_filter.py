import concurrent.futures
from datetime import datetime
import re  # ★ 追加

def process(pipeline_data):
    """Step02: スペシャルユーザー検索 + AI分析"""
    try:
        lv_value = pipeline_data['lv_value']
        config = pipeline_data['config']
        comments_data = pipeline_data['results']['step01_xml_parser']['comments_data']
        
        print(f"Step02 開始: スペシャルユーザー検索 + AI分析 - {lv_value}")
        
        # スペシャルユーザーリストを取得
        special_users = get_special_users_from_config(config)
        
        if not special_users:
            print("スペシャルユーザーが設定されていません")
            return {
                "special_users_found": 0,
                "found_users": []
            }
        
        # コメントからスペシャルユーザーを検索
        found_users_data = find_special_users_in_comments(comments_data, special_users)
        
        if not found_users_data:
            print("スペシャルユーザーが見つかりませんでした")
            return {
                "special_users_found": 0,
                "found_users": []
            }
        
        # AI分析を並列実行
        analyzed_users = perform_ai_analysis_parallel(found_users_data, config)
        
        print(f"Step02 完了: 検出スペシャルユーザー数 {len(analyzed_users)}")
        
        return {
            "special_users_found": len(analyzed_users),
            "found_users": analyzed_users,
            "all_special_users": special_users
        }
        
    except Exception as e:
        print(f"Step02 エラー: {str(e)}")
        raise

def get_special_users_from_config(config):
    """設定からスペシャルユーザーリストを取得"""
    special_users_config = config.get("special_users_config", {})
    users = special_users_config.get("users", {})
    
    user_ids = list(users.keys())
    print(f"設定済みスペシャルユーザー: {user_ids}")
    
    return user_ids

def find_special_users_in_comments(comments_data, special_users):
    """コメントからスペシャルユーザーを検索"""
    found_users = {}
    
    print(f"検索対象コメント数: {len(comments_data)}")
    
    for comment in comments_data:
        user_id = comment.get('user_id', '')
        user_name = comment.get('user_name', '')
        
        if user_id in special_users:
            if user_id not in found_users:
                found_users[user_id] = {
                    'user_id': user_id,
                    'user_name': user_name or f"ユーザー{user_id}",
                    'comments': []
                }
            
            # コメント情報を追加
            comment_data = {
                'no': comment.get('no', ''),
                'date': comment.get('date', ''),
                'text': comment.get('text', ''),
                'premium': comment.get('premium', ''),
                'name': comment.get('user_name', '')
            }
            found_users[user_id]['comments'].append(comment_data)
            print(f"スペシャルユーザーコメント検出: {user_id} - {comment_data['text'][:50]}")
    
    print(f"スペシャルユーザー検出: {list(found_users.keys())}")
    return list(found_users.values())

def perform_ai_analysis_parallel(found_users_data, config):
    """AI分析を並列実行"""
    analyzed_users = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # 各ユーザーのAI分析を並列実行
        future_to_user = {
            executor.submit(analyze_single_user, user_data, config): user_data 
            for user_data in found_users_data
        }
        
        for future in concurrent.futures.as_completed(future_to_user):
            user_data = future_to_user[future]
            try:
                analysis_result = future.result()
                user_data['ai_analysis'] = analysis_result
                analyzed_users.append(user_data)
                print(f"AI分析完了: {user_data['user_id']}")
            except Exception as e:
                print(f"AI分析エラー: {user_data['user_id']} - {str(e)}")
                # エラー時は基本分析で継続
                user_data['ai_analysis'] = generate_basic_analysis(user_data['comments'])
                analyzed_users.append(user_data)
    
    return analyzed_users

def analyze_single_user(user_data, config):
    """単一ユーザーのAI分析を実行"""
    user_id = user_data['user_id']
    comments = user_data['comments']
    
    if not comments:
        return "分析対象のコメントがありません。"
    
    # special_users_configからAI設定を取得
    special_users_config = config.get("special_users_config", {})
    ai_model = special_users_config.get("default_analysis_ai_model", "openai-gpt4o")
    analysis_enabled = special_users_config.get("default_analysis_enabled", True)
    
    print(f"AI分析設定 - モデル: {ai_model}, 有効: {analysis_enabled}")
    
    if not analysis_enabled:
        return generate_basic_analysis(comments)
    
    try:
        if ai_model == "openai-gpt4o":
            return generate_openai_analysis(user_data, config)
        elif ai_model == "google-gemini-2.5-flash":
            return generate_gemini_analysis(user_data, config)
        else:
            print(f"不明なAIモデル: {ai_model}")
            return generate_basic_analysis(comments)
    except Exception as e:
        print(f"AI分析エラー ({ai_model}): {str(e)}")
        return generate_basic_analysis(comments)

def clean_ai_response(ai_response):
    """AI分析結果からコードブロック記法やMarkdown記法を除去"""
    if not ai_response:
        return ""
    
    # コードブロック記法を除去
    ai_response = re.sub(r'```[\w]*\n?', '', ai_response)  # ```html, ```css, ``` など
    ai_response = re.sub(r'```', '', ai_response)  # 残った```も除去
    
    # インラインコード記法を除去
    ai_response = re.sub(r'`([^`]+)`', r'\1', ai_response)  # `code` → code
    
    # Markdown太字記法をHTMLに変換
    ai_response = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', ai_response)
    
    # Markdown見出し記法をHTMLに変換
    ai_response = re.sub(r'^### (.+)$', r'<h3>\1</h3>', ai_response, flags=re.MULTILINE)
    ai_response = re.sub(r'^## (.+)$', r'<h2>\1</h2>', ai_response, flags=re.MULTILINE)
    ai_response = re.sub(r'^# (.+)$', r'<h1>\1</h1>', ai_response, flags=re.MULTILINE)
    
    # 改行をHTMLに変換
    ai_response = ai_response.replace('\n\n', '<br><br>')
    ai_response = ai_response.replace('\n', '<br>')
    
    return ai_response.strip()


def generate_openai_analysis(user_data, config):
    """OpenAI APIを使用してユーザー分析を生成"""
    try:
        import openai
        
        # API設定を取得
        api_settings = config.get("api_settings", {})
        openai_api_key = api_settings.get("openai_api_key", "")
        
        if not openai_api_key:
            print("OpenAI APIキーが設定されていません")
            return generate_basic_analysis(user_data['comments'])
        
        # 放送情報を取得
        broadcast_info = config.get('broadcast_info', {})
        live_title = broadcast_info.get('live_title', '配信タイトル不明')
        
        # コメントデータを整理
        comment_texts = []
        for comment in user_data['comments']:
            timestamp = format_unix_time(comment.get('date', ''))
            text = comment.get('text', '')
            comment_texts.append(f"[{timestamp}] {text}")
        
        user_data_text = "\n".join(comment_texts)
        
        # ユーザー個別のプロンプトを取得
        special_users_config = config.get("special_users_config", {})
        users_config = special_users_config.get("users", {})
        user_id = user_data['user_id']
        
        # 個別ユーザー設定があるかチェック
        if user_id in users_config and users_config[user_id].get("analysis_prompt"):
            analysis_prompt = users_config[user_id]["analysis_prompt"]
            print(f"個別プロンプト使用: {user_id}")
        else:
            analysis_prompt = special_users_config.get("default_analysis_prompt", "")
            print(f"デフォルトプロンプト使用: {user_id}")
        
        # ★★★ 重要：変数置換を実行 ★★★
        analysis_prompt = analysis_prompt.format(
            user=user_data['user_name'],
            lv_title=live_title
        )
        
        system_prompt = "あなたは配信コメントの分析専門家です。ユーザーの行動パターンや特徴を詳しく分析してください。"
        
        full_prompt = f"""
{analysis_prompt}

ユーザーID: {user_data['user_id']}
表示名: {user_data['user_name']}
総コメント数: {len(user_data['comments'])}件

コメント履歴:
{user_data_text}

上記のデータを基に、このユーザーの詳細な分析を行ってください。
分析結果はHTML形式で出力し、<br>タグで改行してください。
"""

        # OpenAI APIを呼び出し
        client = openai.OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        ai_result = response.choices[0].message.content.strip()
        
        # ★★★ 追加：AI結果をクリーニング ★★★
        ai_result = clean_ai_response(ai_result)
        
        # プロンプトと結果をファイルに保存
        save_prompt_to_file("openai", user_data, system_prompt, full_prompt, ai_result)
        
        return ai_result
        
    except Exception as e:
        print(f"OpenAI分析エラー: {str(e)}")
        return generate_basic_analysis(user_data['comments'])

def generate_gemini_analysis(user_data, config):
    """Google Gemini APIを使用してユーザー分析を生成"""
    try:
        import google.generativeai as genai
        
        # API設定を取得
        api_settings = config.get("api_settings", {})
        google_api_key = api_settings.get("google_api_key", "")
        
        if not google_api_key:
            print("Google APIキーが設定されていません")
            return generate_basic_analysis(user_data['comments'])
        
        # Gemini APIを設定
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 放送情報を取得
        broadcast_info = config.get('broadcast_info', {})
        live_title = broadcast_info.get('live_title', '配信タイトル不明')
        
        # コメントデータを整理
        comment_texts = []
        for comment in user_data['comments']:
            timestamp = format_unix_time(comment.get('date', ''))
            text = comment.get('text', '')
            comment_texts.append(f"[{timestamp}] {text}")
        
        user_data_text = "\n".join(comment_texts)
        
        # ユーザー個別のプロンプトを取得
        special_users_config = config.get("special_users_config", {})
        users_config = special_users_config.get("users", {})
        user_id = user_data['user_id']
        
        # 個別ユーザー設定があるかチェック
        if user_id in users_config and users_config[user_id].get("analysis_prompt"):
            analysis_prompt = users_config[user_id]["analysis_prompt"]
            print(f"個別プロンプト使用: {user_id}")
        else:
            analysis_prompt = special_users_config.get("default_analysis_prompt", "")
            print(f"デフォルトプロンプト使用: {user_id}")
        
        # ★★★ 重要：変数置換を実行 ★★★
        analysis_prompt = analysis_prompt.format(
            user=user_data['user_name'],
            lv_title=live_title
        )
        
        full_prompt = f"""
{analysis_prompt}

ユーザーID: {user_data['user_id']}
表示名: {user_data['user_name']}
総コメント数: {len(user_data['comments'])}件

コメント履歴:
{user_data_text}

上記のデータを基に、このユーザーの詳細な分析を日本語で行ってください。
分析結果はHTML形式で出力し、<br>タグで改行してください。
"""

        response = model.generate_content(full_prompt)
        
        # ★★★ 追加：AI結果をクリーニング ★★★
        ai_result = clean_ai_response(response.text)
        
        # プロンプトと結果をファイルに保存
        save_prompt_to_file("gemini", user_data, "", full_prompt, ai_result)
        
        return ai_result
        
    except Exception as e:
        print(f"Gemini分析エラー: {str(e)}")
        return generate_basic_analysis(user_data['comments'])

def save_prompt_to_file(ai_model, user_data, system_prompt, user_prompt, ai_response):
    """プロンプト内容と分析結果をファイルに保存"""
    try:
        import os
        
        # ログディレクトリ作成
        log_dir = os.path.join("logs", "ai_prompts")
        os.makedirs(log_dir, exist_ok=True)
        
        # ファイル名生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = user_data['user_id']
        filename = f"{timestamp}_{ai_model}_{user_id}.txt"
        filepath = os.path.join(log_dir, filename)
        
        # プロンプト詳細をファイルに保存
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"AI分析プロンプト詳細ログ\n")
            f.write(f"{'=' * 60}\n")
            f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"AIモデル: {ai_model.upper()}\n")
            f.write(f"ユーザーID: {user_data['user_id']}\n")
            f.write(f"ユーザー名: {user_data['user_name']}\n")
            f.write(f"コメント数: {len(user_data['comments'])}件\n")
            f.write(f"{'=' * 60}\n\n")
            
            if system_prompt:
                f.write(f"システムプロンプト:\n")
                f.write(f"{'-' * 30}\n")
                f.write(f"{system_prompt}\n\n")
            
            f.write(f"ユーザープロンプト:\n")
            f.write(f"{'-' * 30}\n")
            f.write(f"{user_prompt}\n\n")
            
            f.write(f"AI分析結果:\n")
            f.write(f"{'-' * 30}\n")
            f.write(f"{ai_response}\n\n")
            
            f.write(f"コメント詳細:\n")
            f.write(f"{'-' * 30}\n")
            for i, comment in enumerate(user_data['comments'], 1):
                timestamp = format_unix_time(comment.get('date', ''))
                text = comment.get('text', '')
                f.write(f"{i:3d}. [{timestamp}] {text}\n")
        
        print(f"プロンプトログ保存: {filepath}")
        
    except Exception as e:
        print(f"プロンプトファイル保存エラー: {str(e)}")

def generate_basic_analysis(comments):
    """基本分析を生成"""
    if not comments:
        return "コメントがありません。"
    
    total_comments = len(comments)
    total_chars = sum(len(comment.get('text', '')) for comment in comments)
    avg_chars = total_chars / total_comments if total_comments > 0 else 0
    
    analysis = f"""
        <strong>基本分析</strong><br><br>
        - 総コメント数: {total_comments}件<br>
        - 平均文字数: {avg_chars:.1f}文字<br>
        - コメント傾向: 配信に対して積極的に参加している様子が伺えます。<br>
        - 参加時間帯: 配信全体を通してコメントを投稿しています。<br>
    """
    
    return analysis

def format_unix_time(unix_time_str):
    """UNIX時間を日時表記に変換"""
    try:
        unix_time = int(unix_time_str)
        dt = datetime.fromtimestamp(unix_time)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(unix_time_str)