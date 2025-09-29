import sqlite3
import random
import os

def extract_random_comments(user_id, num_comments=100):
    """指定されたユーザーIDの発言を無作為に取り出す"""

    # データベースに接続
    conn = sqlite3.connect('data/ncv_monitor.db')
    cursor = conn.cursor()

    # 指定されたユーザーIDの全コメントを取得
    cursor.execute(
        "SELECT comment_text FROM comments WHERE user_id = ? AND comment_text IS NOT NULL AND comment_text != ''",
        (user_id,)
    )

    all_comments = cursor.fetchall()
    conn.close()

    if not all_comments:
        print(f"ユーザーID {user_id} のコメントが見つかりませんでした。")
        return []

    print(f"ユーザーID {user_id} の総コメント数: {len(all_comments)}")

    # 無作為に指定された数のコメントを選択
    if len(all_comments) < num_comments:
        print(f"利用可能なコメント数が{len(all_comments)}件のため、全てを取得します。")
        selected_comments = all_comments
    else:
        selected_comments = random.sample(all_comments, num_comments)

    # コメントテキストのみを抽出
    comment_texts = [comment[0] for comment in selected_comments]

    return comment_texts

def save_comments_to_file(comments, filename):
    """コメントをテキストファイルに保存"""

    with open(filename, 'w', encoding='utf-8') as f:
        for i, comment in enumerate(comments, 1):
            f.write(f"{comment}\n")

    print(f"{len(comments)}件のコメントを {filename} に保存しました。")

def main():
    user_id = "21639740"
    output_filename = f"user_{user_id}_comments.txt"

    print(f"ユーザーID {user_id} のコメントを無作為に100件取得中...")

    # コメントを取得
    comments = extract_random_comments(user_id, 100)

    if comments:
        # ファイルに保存
        save_comments_to_file(comments, output_filename)
        print(f"処理完了: {output_filename}")
    else:
        print("取得できるコメントがありませんでした。")

if __name__ == "__main__":
    main()