import concurrent.futures
from datetime import datetime

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
    
    # API設定を取得
    api_settings = config.get("api_settings", {})
    ai_model = api_settings.get("summary_ai_model", "openai-gpt4o")
    
    if not comments:
        return "分析対象のコメントがありません。"
    
    try:
        if ai_model == "openai-gpt4o":
            return generate_openai_analysis(user_data, config)
        elif ai_model == "google-gemini-2.5-flash":
            return generate_gemini_analysis(user_data, config)
        else:
            return generate_basic_analysis(comments)
    except Exception as e:
        print(f"AI分析エラー ({ai_model}): {str(e)}")
        return generate_basic_analysis(comments)

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
        
        # コメントデータを整理
        comment_texts = []
        for comment in user_data['comments']:
            timestamp = format_unix_time(comment.get('date', ''))
            text = comment.get('text', '')
            comment_texts.append(f"[{timestamp}] {text}")
        
        user_data_text = "\n".join(comment_texts)
        
        # プロンプトを構築
        special_users_config = config.get("special_users_config", {})
        analysis_prompt = special_users_config.get("default_analysis_prompt", "")
        
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

        # OpenAI APIを呼び出し
        client = openai.OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは配信コメントの分析専門家です。ユーザーの行動パターンや特徴を詳しく分析してください。"},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        ai_result = response.choices[0].message.content.strip()
        
        # 分析結果にメタ情報を追加
        metadata = f"""
<div style="background-color: #f0f8ff; padding: 10px; margin: 10px 0; border-left: 4px solid #0066cc;">
<strong>AI分析情報</strong><br>
分析モデル: OpenAI GPT-4o<br>
分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
分析対象: {len(user_data['comments'])}件のコメント
</div>
"""
        
        return metadata + ai_result
        
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
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # コメントデータを整理
        comment_texts = []
        for comment in user_data['comments']:
            timestamp = format_unix_time(comment.get('date', ''))
            text = comment.get('text', '')
            comment_texts.append(f"[{timestamp}] {text}")
        
        user_data_text = "\n".join(comment_texts)
        
        # プロンプトを構築
        special_users_config = config.get("special_users_config", {})
        analysis_prompt = special_users_config.get("default_analysis_prompt", "")
        
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
        
        metadata = f"""
<div style="background-color: #f0f8ff; padding: 10px; margin: 10px 0; border-left: 4px solid #0066cc;">
<strong>AI分析情報</strong><br>
分析モデル: Google Gemini 2.0 Flash<br>
分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
分析対象: {len(user_data['comments'])}件のコメント
</div>
"""
        
        return metadata + response.text
        
    except Exception as e:
        print(f"Gemini分析エラー: {str(e)}")
        return generate_basic_analysis(user_data['comments'])

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