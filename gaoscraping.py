import requests
from bs4 import BeautifulSoup
import re
import json
import os

# 設定
CONFIG = {
    "base_url": "https://saveniconicocomment.com/link/linkPage.html",
    "output_file": "comments.json",
    "encoding": "utf-8"
}

def debuglog(msg):
    print(f"[DEBUG] {msg}", flush=True)

def fetch_links():
    res = requests.get(CONFIG["base_url"])
    res.encoding = 'utf-8'  # エンコーディング明示指定
    res.raise_for_status()
    
    soup = BeautifulSoup(res.text, "html.parser")
    links = [a["href"] for a in soup.find_all("a", href=True, string="Link") 
             if "post/updated_" in a["href"]]
    return links

def parse_post_page(url):
    res = requests.get(url)
    res.encoding = 'utf-8'  # エンコーディング明示指定
    res.raise_for_status()
    
    soup = BeautifulSoup(res.text, "html.parser")

    # OpenTime取得
    timestamp = None
    open_time_tag = soup.find(string=re.compile("OpenTime"))
    if open_time_tag:
        match = re.search(r"OpenTime:\s*(\d+)", open_time_tag)
        if match:
            timestamp = int(match.group(1))

    results = []
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if "|" in text and "-" in text and ":" in text:
            m = re.match(r"(\d+)\s*\|\s*([\d:]+)\s*-\s*(.+?)\s*:\s*(.+)", text)
            if m:
                user_link = p.find("a", href=re.compile("nicovideo.jp/user/"))
                user_id = None
                if user_link:
                    uid_match = re.search(r"user/(\d+)", user_link["href"])
                    if uid_match:
                        user_id = uid_match.group(1)

                results.append({
                    "user_id": user_id,
                    "user_name": m.group(3),
                    "comment_text": m.group(4),
                    "comment_no": int(m.group(1)),
                    "timestamp": timestamp,
                    "elapsed_time": m.group(2)
                })
    return results

def main():
    links = fetch_links()
    debuglog(f"{len(links)} 件のリンクを発見")

    all_comments = []
    for link in links:
        debuglog(f"処理中: {link}")
        comments = parse_post_page(link)
        debuglog(f"{len(comments)} 件のコメント取得")
        all_comments.extend(comments)

    debuglog(f"合計 {len(all_comments)} 件を収集")
    
    # ファイル保存
    output_path = os.path.abspath(CONFIG["output_file"])
    with open(output_path, 'w', encoding=CONFIG["encoding"]) as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=2)
    
    debuglog(f"保存完了: {output_path}")

if __name__ == "__main__":
    main()