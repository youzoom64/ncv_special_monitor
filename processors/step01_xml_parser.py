import xml.etree.ElementTree as ET
import os
import json
from datetime import datetime

def process(pipeline_data):
    """Step01: XMLコメント解析 + 統合JSON作成"""
    try:
        xml_path = pipeline_data['xml_path']
        lv_value = pipeline_data['lv_value']
        subfolder_name = pipeline_data['subfolder_name']
        
        print(f"Step01 開始: XMLコメント解析 - {lv_value}")
        
        # XMLファイルの存在確認
        if not os.path.exists(xml_path):
            raise Exception(f"XMLファイルが見つかりません: {xml_path}")
        
        # XMLをパースしてコメントデータを抽出
        comments_data = parse_ncv_xml(xml_path)
        
        # 放送情報を抽出
        broadcast_info = extract_broadcast_info(xml_path)
        
        # 統合JSONを作成
        integrated_data = create_integrated_json(lv_value, subfolder_name, broadcast_info, comments_data)
        
        # JSONファイルを保存
        save_json_files(lv_value, subfolder_name, integrated_data, comments_data)
        
        print(f"Step01 完了: コメント数 {len(comments_data)}")
        
        return {
            "comments_count": len(comments_data),
            "comments_data": comments_data,
            "broadcast_info": broadcast_info,
            "integrated_data": integrated_data,
            "xml_path": xml_path
        }
        
    except Exception as e:
        print(f"Step01 エラー: {str(e)}")
        raise

def parse_ncv_xml(xml_path):
    """NCVのXMLファイルからコメントデータを解析"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        comments = []
        
        # chat要素を検索（名前空間対応）
        chat_elements = root.findall('.//chat')
        if not chat_elements:
            # 名前空間がある場合
            namespaces = {'ncv': 'http://posite-c.jp/niconamacommentviewer/commentlog/'}
            chat_elements = root.findall('.//ncv:chat', namespaces)
        
        print(f"XMLから{len(chat_elements)}個のコメントを検出")
        
        for chat in chat_elements:
            try:
                comment_date = int(chat.get('date', 0))
                if comment_date == 0:
                    continue
                
                # コメントデータを構築
                comment_data = {
                    "no": int(chat.get('no', 0)),
                    "user_id": chat.get('user_id', ''),
                    "user_name": chat.get('name', ''),
                    "text": chat.text or '',
                    "date": comment_date,
                    "premium": int(chat.get('premium', 0)),
                    "anonymity": 'anonymity' in chat.attrib
                }
                
                comments.append(comment_data)
                
            except (ValueError, TypeError) as e:
                print(f"コメント解析エラー: {str(e)}")
                continue
        
        # 時系列順にソート
        comments.sort(key=lambda x: x['date'])
        
        print(f"有効なコメント: {len(comments)}個")
        return comments
        
    except Exception as e:
        print(f"XML解析エラー: {str(e)}")
        raise

def extract_broadcast_info(xml_path):
    """XMLから放送情報を抽出"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 名前空間を考慮
        ns = {'ncv': 'http://posite-c.jp/niconamacommentviewer/commentlog/'}
        
        # LiveInfo取得
        live_info = root.find('.//LiveInfo', ns) or root.find('.//LiveInfo')
        player_status = root.find('.//PlayerStatus', ns) or root.find('.//PlayerStatus')
        
        broadcast_info = {
            'live_title': get_text_content(live_info, './/LiveTitle'),
            'broadcaster': get_text_content(live_info, './/Broadcaster'),
            'community_name': get_text_content(live_info, './/CommunityName'),
            'start_time': get_text_content(live_info, './/StartTime'),
            'end_time': get_text_content(live_info, './/EndTime'),
            'watch_count': get_text_content(player_status, './/WatchCount'),
            'comment_count': get_text_content(player_status, './/CommentCount'),
            'owner_id': get_text_content(player_status, './/OwnerId'),
            'owner_name': get_text_content(player_status, './/OwnerName')
        }
        
        return broadcast_info
        
    except Exception as e:
        print(f"放送情報抽出エラー: {str(e)}")
        return {}

def create_integrated_json(lv_value, subfolder_name, broadcast_info, comments_data):
    """統合JSONデータを作成"""
    integrated_data = {
        "lv_value": lv_value,
        "timestamp": datetime.now().isoformat(),
        "subfolder_name": subfolder_name,
        "live_title": broadcast_info.get('live_title', ''),
        "broadcaster": broadcast_info.get('broadcaster', ''),
        "start_time": broadcast_info.get('start_time', ''),
        "end_time": broadcast_info.get('end_time', ''),
        "owner_id": broadcast_info.get('owner_id', ''),
        "owner_name": broadcast_info.get('owner_name', ''),
        "watch_count": broadcast_info.get('watch_count', ''),
        "comment_count": broadcast_info.get('comment_count', ''),
        "total_comments_parsed": len(comments_data),
        "special_user_analysis": {}  # Step02で追加される
    }
    
    return integrated_data

def save_json_files(lv_value, subfolder_name, integrated_data, comments_data):
    """JSONファイルを保存"""
    try:
        # 出力ディレクトリを作成
        broadcast_dir = os.path.join("SpecialUser", f"{subfolder_name}_{lv_value}")
        os.makedirs(broadcast_dir, exist_ok=True)
        
        # 統合JSONを保存
        integrated_json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
        with open(integrated_json_path, 'w', encoding='utf-8') as f:
            json.dump(integrated_data, f, ensure_ascii=False, indent=2)
        
        # コメントJSONを保存
        comments_json_path = os.path.join(broadcast_dir, f"{lv_value}_comments.json")
        with open(comments_json_path, 'w', encoding='utf-8') as f:
            json.dump(comments_data, f, ensure_ascii=False, indent=2)
        
        print(f"JSONファイル保存完了: {broadcast_dir}")
        
    except Exception as e:
        print(f"JSONファイル保存エラー: {str(e)}")
        raise

def get_text_content(element, xpath):
    """XMLから安全にテキスト取得"""
    if element is None:
        return ""
    found = element.find(xpath)
    return found.text if found is not None and found.text else ""