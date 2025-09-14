import xml.etree.ElementTree as ET
import os
import json
from datetime import datetime

def strip_namespace(elem):
    """XMLの全要素から名前空間を剥がす"""
    for e in elem.iter():
        if isinstance(e.tag, str) and '}' in e.tag:
            e.tag = e.tag.split('}', 1)[1]
    return elem

def process(pipeline_data):
    """Step01: XMLコメント解析 + 統合JSON作成"""
    try:
        xml_path = pipeline_data['xml_path']
        lv_value = pipeline_data['lv_value']
        subfolder_name = pipeline_data['subfolder_name']

        print(f"Step01 開始: XMLコメント解析 - {lv_value}")
        print(f"[DEBUG] XML file path: {xml_path}")
        print(f"[DEBUG] File exists: {os.path.exists(xml_path)}")

        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"XMLファイルが見つかりません: {xml_path}")

        # コメント解析
        print("[DEBUG] コメントデータ解析開始")
        comments_data = parse_ncv_xml(xml_path)
        print(f"[DEBUG] コメントデータ解析完了: {len(comments_data)}件")

        # 放送情報解析
        print("[DEBUG] 放送情報抽出開始")
        broadcast_info = extract_broadcast_info(xml_path)
        print(f"[DEBUG] 放送情報抽出完了: {broadcast_info}")

        # 統合データ作成
        print("[DEBUG] 統合JSON作成開始")
        integrated_data = create_integrated_json(lv_value, subfolder_name, broadcast_info, comments_data)

        # 保存
        print("[DEBUG] JSONファイル保存開始")
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
        print(f"Step01 エラー: {e}")
        import traceback
        traceback.print_exc()
        raise

def parse_ncv_xml(xml_path):
    """NCVのXMLファイルからコメントデータを解析"""
    tree = ET.parse(xml_path)
    root = strip_namespace(tree.getroot())

    comments = []
    chat_elements = root.findall('.//chat')
    print(f"XMLから{len(chat_elements)}個のコメントを検出")

    for chat in chat_elements:
        try:
            comment_date = int(chat.get('date', 0))
            if comment_date == 0:
                continue
            comments.append({
                "no": int(chat.get('no', 0)),
                "user_id": chat.get('user_id', ''),
                "user_name": chat.get('name', ''),
                "text": chat.text or '',
                "date": comment_date,
                "premium": int(chat.get('premium', 0)),
                "anonymity": 'anonymity' in chat.attrib
            })
        except (ValueError, TypeError) as e:
            print(f"コメント解析エラー: {e}")
            continue

    comments.sort(key=lambda x: x['date'])
    print(f"有効なコメント: {len(comments)}個")
    return comments

def extract_broadcast_info(xml_path):
    """XMLから放送情報を抽出（名前空間剥がし後）"""
    tree = ET.parse(xml_path)
    root = strip_namespace(tree.getroot())

    live_info = root.find('LiveInfo')
    player_status = root.find('PlayerStatus')
    stream = player_status.find('Stream') if player_status is not None else None

    broadcast_info = {
        "live_title": get_text_content(live_info, "LiveTitle"),
        "broadcaster": get_text_content(live_info, "Broadcaster"),
        "community_name": get_text_content(live_info, "CommunityName"),
        "start_time": get_text_content(live_info, "StartTime"),
        "end_time": get_text_content(live_info, "EndTime"),
        "watch_count": get_text_content(stream, "WatchCount"),
        "comment_count": get_text_content(stream, "CommentCount"),
        "owner_id": get_text_content(stream, "OwnerId"),
        "owner_name": get_text_content(stream, "OwnerName")
    }

    return broadcast_info

def get_text_content(parent, tag):
    """子タグのテキストを安全に取得"""
    if parent is None:
        return ""
    found = parent.find(tag)
    return (found.text or "").strip() if (found is not None and found.text) else ""

def create_integrated_json(lv_value, subfolder_name, broadcast_info, comments_data):
    """統合JSONデータを作成"""
    return {
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
        "special_user_analysis": {}
    }

def save_json_files(lv_value, subfolder_name, integrated_data, comments_data):
    """JSONファイルを保存"""
    broadcast_dir = os.path.join("SpecialUser", "BroadCastData", subfolder_name, lv_value)
    os.makedirs(broadcast_dir, exist_ok=True)

    with open(os.path.join(broadcast_dir, "data.json"), 'w', encoding='utf-8') as f:
        json.dump(integrated_data, f, ensure_ascii=False, indent=2)

    with open(os.path.join(broadcast_dir, "comments.json"), 'w', encoding='utf-8') as f:
        json.dump(comments_data, f, ensure_ascii=False, indent=2)

    print(f"JSONファイル保存完了: {broadcast_dir}")
