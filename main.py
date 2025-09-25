import os
import tkinter as tk

# GUIパッケージからメインウィンドウをimport
from gui import NCVSpecialMonitorGUI

def main():
    print("[DEBUG] NCV Special Monitor 起動開始")

    # 必要なディレクトリを作成
    print("[DEBUG] ディレクトリ作成: config, logs")
    os.makedirs("config", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    print("[DEBUG] Tkinter初期化開始")
    root = tk.Tk()
    print("[DEBUG] NCVSpecialMonitorGUI初期化開始")
    app = NCVSpecialMonitorGUI(root)
    print("[DEBUG] GUI初期化完了、メインループ開始")
    root.mainloop()

if __name__ == "__main__":
    main()