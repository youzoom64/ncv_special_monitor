import os
import json
import shutil
from datetime import datetime

def process(pipeline_data):
    """Step03: HTML生成"""
    try:
        lv_value = pipeline_data['lv_value']
        subfolder_name = pipeline_data['subfolder_name']
        config = pipeline_data['config']
        
        step02_results = pipeline_data['results']['step02_special_user_filter']
        step01_results = pipeline_data['results']['step01_xml_parser']
        
        found_users = step02_results['found_users']
        broadcast_info = step01_results['broadcast_info']
        integrated_data = step01_results['integrated_data']
        
        print(f"Step03 開始: HTML生成 - {lv_value}")
        
        if not found_users:
            print("スペシャルユーザーが見つからないため、HTML生成をスキップします")
            return {
                "html_generated": False,
                "reason": "no_special_users"
            }
        
        generated_files = []
        
        # 統合JSONを更新（AI分析結果を追加）
        update_integrated_json(lv_value, subfolder_name, found_users, integrated_data)
        
        # 各スペシャルユーザーのHTMLを生成
        for user_data in found_users:
            files = create_special_user_pages(user_data, broadcast_info, lv_value, subfolder_name, config)
            generated_files.extend(files)
        
        print(f"Step03 完了: 生成ファイル数 {len(generated_files)}")
        
        return {
            "html_generated": True,
            "generated_files": generated_files,
            "users_processed": len(found_users)
        }
        
    except Exception as e:
        print(f"Step03 エラー: {str(e)}")
        raise

def update_integrated_json(lv_value, subfolder_name, found_users, integrated_data):
    """統合JSONにAI分析結果を追加"""
    try:
        # AI分析結果を統合データに追加
        for user_data in found_users:
            user_id = user_data['user_id']
            integrated_data['special_user_analysis'][user_id] = {
                'user_name': user_data['user_name'],
                'comment_count': len(user_data['comments']),
                'ai_analysis': user_data.get('ai_analysis', ''),
                'analysis_timestamp': datetime.now().isoformat()
            }
        
        # 更新された統合JSONを保存
        broadcast_dir = os.path.join("SpecialUser", f"{subfolder_name}_{lv_value}")
        integrated_json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
        
        with open(integrated_json_path, 'w', encoding='utf-8') as f:
            json.dump(integrated_data, f, ensure_ascii=False, indent=2)
        
        print(f"統合JSON更新完了: {integrated_json_path}")
        
    except Exception as e:
        print(f"統合JSON更新エラー: {str(e)}")

def create_special_user_pages(user_data, broadcast_info, lv_value, subfolder_name, config):
    """スペシャルユーザーのHTMLページを生成"""
    try:
        user_id = user_data['user_id']
        user_name = user_data['user_name']
        comments = user_data['comments']
        
        print(f"HTMLページ生成中: {user_id} ({user_name})")
        
        # 出力ディレクトリ作成
        special_user_dir = os.path.join("SpecialUser", f"special_user_{user_id}")
        os.makedirs(special_user_dir, exist_ok=True)
        
        # テンプレートディレクトリ
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        
        # CSS/JSファイルをコピー
        copy_static_files(template_dir, special_user_dir)
        
        generated_files = []
        
        # 1. 個別詳細ページ生成
        detail_file = create_user_detail_page(user_data, broadcast_info, template_dir, special_user_dir, lv_value, subfolder_name, config)
        generated_files.append(detail_file)
        
        # 2. 一覧ページ更新
        list_file = update_user_list_page(user_data, broadcast_info, template_dir, special_user_dir, lv_value, subfolder_name)
        generated_files.append(list_file)
        
        print(f"HTMLページ生成完了: {user_id}")
        return generated_files
        
    except Exception as e:
        print(f"HTMLページ生成エラー: {str(e)}")
        raise

def create_user_detail_page(user_data, broadcast_info, template_dir, output_dir, lv_value, subfolder_name, config):
    """個別ユーザー詳細ページを生成"""
    user_id = user_data['user_id']
    
    # テンプレートファイルパス
    template_path = os.path.join(template_dir, 'user_detail.html')
    if not os.path.exists(template_path):
        raise Exception(f"テンプレートファイルが見つかりません: {template_path}")
    
    # テンプレート読み込み
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # コメント行を生成
    comment_rows = generate_comment_rows(user_data['comments'], broadcast_info.get('start_time', ''))
    
    # AI分析結果を取得
    analysis_text = user_data.get('ai_analysis', 'AI分析結果がありません。')
    
    # テンプレート変数を置換
    html_content = template.replace('{{broadcast_title}}', broadcast_info.get('live_title', 'タイトル不明'))
    html_content = html_content.replace('{{start_time}}', format_start_time(broadcast_info.get('start_time', '')))
    html_content = html_content.replace('{{user_avatar}}', get_user_icon_path(user_data['user_id']))
    html_content = html_content.replace('{{user_name}}', user_data['user_name'])
    html_content = html_content.replace('{{user_profile_url}}', f"https://www.nicovideo.jp/user/{user_data['user_id']}")
    html_content = html_content.replace('{{user_id}}', user_data['user_id'])
    html_content = html_content.replace('{{comment_rows}}', comment_rows)
    html_content = html_content.replace('{{analysis_text}}', analysis_text)
    
    # ファイル保存
    output_filename = f"{subfolder_name}_{lv_value}_detail.html"
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"個別ページ生成: {output_path}")
    return output_path

def update_user_list_page(user_data, broadcast_info, template_dir, output_dir, lv_value, subfolder_name):
    """一覧ページを更新"""
    template_path = os.path.join(template_dir, 'user_list.html')
    list_file_path = os.path.join(output_dir, "list.html")
    
    # 既存の一覧ページがある場合は読み込み
    existing_items = []
    if os.path.exists(list_file_path):
        existing_items = load_existing_broadcast_items(list_file_path)
    
    # 新しい放送アイテムを追加
    new_item = generate_broadcast_item(user_data, broadcast_info, lv_value, subfolder_name)
    existing_items.append(new_item)
    
    # テンプレートを読み込み
    if not os.path.exists(template_path):
        print(f"一覧テンプレートが見つかりません: {template_path}")
        return list_file_path
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 全ての放送アイテムを結合
    all_items = '\n'.join(existing_items)
    
    # テンプレート変数を置換
    html_content = template.replace('{{broadcaster_name}}', user_data['user_name'])
    html_content = html_content.replace('{{thumbnail_url}}', get_user_icon_path(user_data['user_id']))
    html_content = html_content.replace('{{broadcast_items}}', all_items)
    
    # ファイル保存
    with open(list_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"一覧ページ更新: {list_file_path}")
    return list_file_path

def generate_comment_rows(comments, start_time_str):
    """コメントテーブルの行を生成（配信内時間計算付き）"""
    rows = []
    
    # 放送開始時刻を取得
    try:
        start_time = int(start_time_str) if start_time_str else 0
    except:
        start_time = 0
    
    for i, comment in enumerate(comments, 1):
        comment_timestamp = comment.get('date', 0)
        date_str = format_unix_time(comment_timestamp)
        
        # 配信内時間を計算
        if start_time and comment_timestamp:
            try:
                elapsed_seconds = int(comment_timestamp) - start_time
                elapsed_time = format_elapsed_time(elapsed_seconds)
            except:
                elapsed_time = "00:00:00"
        else:
            elapsed_time = "00:00:00"
        
        row = f'''
        <tr>
            <td>{i}</td>
            <td>{elapsed_time}</td>
            <td>{date_str}</td>
            <td><b style="font-size: 25px;">{escape_html(comment.get('text', ''))}</b></td>
        </tr>'''
        rows.append(row)
    
    return '\n'.join(rows)

def generate_broadcast_item(user_data, broadcast_info, lv_value, subfolder_name):
    """放送アイテムを生成"""
    if not user_data['comments']:
        return "<p>コメントがありません</p>"
    
    first_comment = user_data['comments'][0].get('text', '') if user_data['comments'] else ''
    last_comment = user_data['comments'][-1].get('text', '') if user_data['comments'] else ''
    
    item = f'''
        <div class="link-item">
            <p class="separator">―――――――――――――――――――――――――――――――――――――――――――</p>
            <p class="start-time">開始時間: {format_start_time(broadcast_info.get('start_time', ''))}</p>
            <div class="comment-preview">
                <p>初コメ: {escape_html(first_comment)}</p>
                <p>最終コメ: {escape_html(last_comment)}</p>
            </div>
            
            <div class="broadcast-link">
                <a href="{subfolder_name}_{lv_value}_detail.html">{broadcast_info.get('live_title', 'タイトル不明')}: における{user_data['user_name']}のコメント分析</a>
            </div>
        </div>
    '''
    
    return item

def load_existing_broadcast_items(list_file_path):
    """既存の一覧ページから放送アイテムを抽出"""
    try:
        with open(list_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 簡単な方法：既存のlink-itemを抽出
        import re
        pattern = r'<div class="link-item">.*?</div>'
        matches = re.findall(pattern, content, re.DOTALL)
        return matches
        
    except Exception as e:
        print(f"既存アイテム読み込みエラー: {str(e)}")
        return []

def copy_static_files(template_dir, output_dir):
    """CSS/JSファイルを出力ディレクトリにコピー"""
    try:
        # cssディレクトリをコピー
        css_src = os.path.join(template_dir, 'css')
        css_dst = os.path.join(output_dir, 'css')
        if os.path.exists(css_src):
            shutil.copytree(css_src, css_dst, dirs_exist_ok=True)
        
        # jsディレクトリをコピー
        js_src = os.path.join(template_dir, 'js')
        js_dst = os.path.join(output_dir, 'js')
        if os.path.exists(js_src):
            shutil.copytree(js_src, js_dst, dirs_exist_ok=True)
        
        # assetsディレクトリをコピー
        assets_src = os.path.join(template_dir, 'assets')
        assets_dst = os.path.join(output_dir, 'assets')
        if os.path.exists(assets_src):
            shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)
            
    except Exception as e:
        print(f"静的ファイルコピーエラー: {str(e)}")

def get_user_icon_path(user_id):
    """ニコニコ動画のユーザーアイコンパスを生成"""
    if len(user_id) <= 4:
        return f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{user_id}.jpg"
    else:
        path_prefix = user_id[:-4]
        return f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{path_prefix}/{user_id}.jpg"

def format_unix_time(unix_time_str):
    """UNIX時間を日時表記に変換"""
    try:
        unix_time = int(unix_time_str)
        dt = datetime.fromtimestamp(unix_time)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(unix_time_str)

def format_start_time(start_time_str):
    """開始時間をフォーマット"""
    try:
        unix_time = int(start_time_str)
        dt = datetime.fromtimestamp(unix_time)
        return dt.strftime('%Y/%m/%d(%a) %H:%M')
    except:
        return str(start_time_str)

def format_elapsed_time(seconds):
    """経過秒数を時:分:秒形式に変換"""
    try:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    except:
        return "00:00:00"

def escape_html(text):
    """HTMLエスケープ"""
    if not text:
        return ""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))