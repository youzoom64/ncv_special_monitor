import requests
from bs4 import BeautifulSoup
import json

def fetch_nico_user_name(user_id: str):
    url = f"https://www.nicovideo.jp/user/{user_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"  # 明示的にUTF-8指定
        soup = BeautifulSoup(response.text, "lxml")

        # 1. metaタグから取得
        meta_tag = soup.find("meta", {"property": "profile:username"})
        if meta_tag and meta_tag.get("content"):
            return meta_tag["content"]

        # 2. JSON-LDから取得
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, dict) and "name" in data:
                    return data["name"]
            except json.JSONDecodeError:
                pass

        # 3. クラス名から取得
        nickname_element = soup.find(class_="UserDetailsHeader-nickname")
        if nickname_element:
            return nickname_element.get_text(strip=True)

        return None

    except requests.RequestException as e:
        print(f"HTTPエラー: {e}")
        return None

if __name__ == "__main__":
    user_id = "8908639"  # テスト用
    name = fetch_nico_user_name(user_id)
    if name:
        print(f"取得成功: {name}")
    else:
        print("取得できませんでした")
