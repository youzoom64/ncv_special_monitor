import os
import tkinter as tk

# GUIパッケージからメインウィンドウをimport
from gui import NCVSpecialMonitorGUI

def main():
    # 必要なディレクトリを作成
    os.makedirs("config", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    root = tk.Tk()
    app = NCVSpecialMonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()