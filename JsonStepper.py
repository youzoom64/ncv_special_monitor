import json
import tkinter as tk
from tkinter import filedialog, messagebox
import pyperclip  # pip install pyperclip

class JsonClipboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JSONクリップボードツール")

        # 入力欄（段階的に10段階まで）
        self.entries = []
        for i in range(10):
            lbl = tk.Label(root, text=f"キー {i+1}:")
            lbl.grid(row=i, column=0, padx=5, pady=2, sticky="e")
            ent = tk.Entry(root, width=30)
            ent.grid(row=i, column=1, padx=5, pady=2)
            self.entries.append(ent)

        # JSONロードボタン
        tk.Button(root, text="JSONファイルを開く", command=self.load_json).grid(row=0, column=2, padx=10)

        # 出力件数表示
        self.count_var = tk.StringVar(value="要素数: 0")
        tk.Label(root, textvariable=self.count_var).grid(row=11, column=0, columnspan=2, pady=5)

        # コントロールボタン
        tk.Button(root, text="スタート", command=self.start).grid(row=12, column=0, pady=5)
        tk.Button(root, text="次", command=self.next_value).grid(row=12, column=1, pady=5)

        # 詳細表示
        self.text_box = tk.Text(root, width=50, height=20)
        self.text_box.grid(row=0, column=3, rowspan=13, padx=10, pady=5)

        # データ管理用
        self.values = []
        self.index = 0

    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.json_data = json.load(f)
            messagebox.showinfo("OK", "JSONファイルを読み込みました")
        except Exception as e:
            messagebox.showerror("Error", f"JSON読み込み失敗: {e}")

    def get_target_values(self):
        data = self.json_data
        try:
            for ent in self.entries:
                key = ent.get().strip()
                if not key:
                    break
                if isinstance(data, list):
                    data = [d[key] for d in data if isinstance(d, dict) and key in d]
                elif isinstance(data, dict) and key in data:
                    data = data[key]
                else:
                    return []
            if isinstance(data, list):
                return data
            else:
                return [data]
        except Exception:
            return []

    def start(self):
        if not hasattr(self, "json_data"):
            messagebox.showerror("Error", "JSONファイルを先に読み込んでください")
            return
        self.values = self.get_target_values()
        self.index = 0
        self.count_var.set(f"要素数: {len(self.values)}")
        if self.values:
            self.copy_to_clipboard(self.values[0])
            self.show_detail(self.values[0])

    def next_value(self):
        if not self.values:
            messagebox.showwarning("警告", "要素がありません")
            return
        self.index += 1
        if self.index >= len(self.values):
            messagebox.showinfo("完了", "全ての要素をコピーしました")
            return
        val = self.values[self.index]
        self.copy_to_clipboard(val)
        self.show_detail(val)
        self.count_var.set(f"残り: {len(self.values) - self.index - 1}")

    def copy_to_clipboard(self, val):
        pyperclip.copy(str(val))
        DEBUG = f"クリップボードにコピー: {val}"
        print(DEBUG)

    def show_detail(self, val):
        self.text_box.insert(tk.END, str(val) + "\n")
        self.text_box.see(tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = JsonClipboardApp(root)
    root.mainloop()
