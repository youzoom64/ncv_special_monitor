# -*- coding: utf-8 -*-
"""
specialuser_follow_fetcher.py  — 完全修正版
- Selenium(ヘッドレス)で描画後DOMを取得し、無限スクロールで全件読む
- a: 等の非数値IDは完全スキップ
- follow.json は「新規のみ」追記して保存。in-place比較バグを排除
- 破損対策に原子的書き込み(os.replace)＆バックアップ
- DEBUGログと debug_follow_{id}.html を出力
"""

import os
import re
import json
import logging
import time
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ====== パス類 ======
CONFIG_PATH = Path("config") / "ncv_special_config.json"
SPECIALUSER_ROOT = Path("SpecialUser")
BASE_URL = "https://www.nicovideo.jp/user/{}/follow"

# ====== LOG ======
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
DEBUGLOG = logging.getLogger("specialuser")

# ====== Windows用ファイル名サニタイズ ======
INVALID_FS_CHARS = r'[\\/:*?"<>|]'
RESERVED = {"CON","PRN","AUX","NUL",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}

def sanitize_for_fs(name: str) -> str:
    s = re.sub(INVALID_FS_CHARS, "_", str(name).strip())
    if s.upper() in RESERVED:
        s += "_"
    return s[:120]

# ====== 設定ロード ======
def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def should_skip_user_id(user_id: str) -> bool:
    if user_id.startswith("a:"):
        DEBUGLOG.warning(f"Skip a: user_id: {user_id}")
        return True
    if not user_id.isdigit():
        DEBUGLOG.warning(f"Skip non-numeric user_id: {user_id}")
        return True
    return False

# ====== Selenium 起動 ======
def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=ja-JP")
    # UA固定（必要に応じて）
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=opts)
    return driver

# ====== 無限スクロールして全件出す ======
def load_all_items(driver, min_wait=0.5, max_rounds=30, idle_threshold=2):
    """
    画面最下部までスクロールし、要素数が増えなくなるまで繰り返す。
    max_rounds と idle_threshold で早期終了。
    """
    last_count = 0
    idle = 0
    for i in range(max_rounds):
        elems = driver.find_elements(By.CSS_SELECTOR, "div.UserItem a.UserItem-link")
        count = len(elems)
        DEBUGLOG.debug(f"[SCROLL] round={i} items={count}")
        if count <= last_count:
            idle += 1
        else:
            idle = 0
        if idle >= idle_threshold:
            break
        # 下までスクロール
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(min_wait)
        last_count = count

# ====== 1ユーザーのフォロー抽出 ======
def fetch_follow_list(user_id: str, driver) -> list[dict]:
    url = BASE_URL.format(user_id)
    DEBUGLOG.info(f"Accessing {url}")
    driver.get(url)

    # 最初の出現待ち
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.InfiniteList, div.UserItem"))
        )
    except Exception as e:
        DEBUGLOG.warning(f"List container not found within timeout for {user_id}: {e}")

    # 無限スクロールで増分を読み切る
    load_all_items(driver)

    html = driver.page_source
    debug_path = f"debug_follow_{user_id}.html"
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(html)
    DEBUGLOG.debug(f"Saved page source to {debug_path} (length={len(html)})")

    soup = BeautifulSoup(html, "html.parser")
    a_tags = soup.select("div.UserItem a.UserItem-link")
    DEBUGLOG.debug(f"Found {len(a_tags)} <a.UserItem-link> elements for {user_id}")

    follows = []
    for a in a_tags:
        href = a.get("href") or ""
        name_tag = a.select_one("h1.UserItem-nickname")
        name = name_tag.get_text(strip=True) if name_tag else ""
        # /user/xxxxx を抽出（相対・絶対両対応）
        fid = ""
        try:
            path = urlparse(href).path  # '/user/50028270'
            parts = path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "user":
                fid = parts[1]
            elif "/user/" in href:
                fid = href.split("/user/")[1].split("?")[0].split("#")[0]
        except Exception:
            pass

        if fid and name:
            follows.append({"follow_user_name": name, "follow_user_id": fid})
            DEBUGLOG.debug(f"Parsed follow: id={fid} name={name}")

    DEBUGLOG.info(f"Collected {len(follows)} follows for {user_id}")
    return follows

# ====== 既存読込 ======
def read_existing_follow(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        DEBUGLOG.warning(f"Broken JSON at {path}: {e}")
        # 壊れていたらバックアップして空扱い
        try:
            path.rename(path.with_suffix(".broken.json"))
        except Exception:
            pass
        return []

# ====== 追記ロジック（非in-placeで確実に差分判定） ======
def build_merged(existing: list, new_items: list) -> tuple[list, int]:
    existing_ids = {str(x.get("follow_user_id", "")) for x in existing}
    to_add = [it for it in new_items if str(it.get("follow_user_id", "")) not in existing_ids]
    merged = existing + to_add  # 新しいリストを作る（in-place禁止）
    return merged, len(to_add)

# ====== 原子的書き込み ======
def atomic_write_json(path: Path, payload: list):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)  # 原子的置換（WinでもOK）

# ====== 保存 ======
def update_follow_json(user_id: str, display_name: str, follows: list[dict]) -> None:
    if not follows:
        DEBUGLOG.warning(f"No follows found for {user_id} ({display_name}); keep existing as-is")
        return

    safe_dir = SPECIALUSER_ROOT / f"{sanitize_for_fs(user_id)}_{sanitize_for_fs(display_name)}"
    safe_dir.mkdir(parents=True, exist_ok=True)
    follow_path = safe_dir / "follow.json"

    existing = read_existing_follow(follow_path)
    merged, added = build_merged(existing, follows)
    DEBUGLOG.info(f"Appended {added} new follows")

    if added == 0 and follow_path.exists():
        DEBUGLOG.info(f"No changes for {user_id} ({display_name})")
        return

    atomic_write_json(follow_path, merged)
    DEBUGLOG.info(f"Wrote {follow_path} with {len(merged)} entries")
    DEBUGLOG.debug(f"Content sample: {merged[:3]}")

# ====== メイン ======
def main():
    cfg = load_config()
    users = cfg.get("special_users_config", {}).get("users", {})

    driver = setup_driver()
    try:
        for user_id, info in users.items():
            display_name = str(info.get("display_name", "")).strip()
            if not display_name:
                DEBUGLOG.warning(f"Missing display_name for {user_id}, skip")
                continue
            if should_skip_user_id(user_id):
                continue

            DEBUGLOG.info(f"Fetching follows for {user_id} ({display_name})...")
            follows = fetch_follow_list(user_id, driver)
            update_follow_json(user_id, display_name, follows)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
