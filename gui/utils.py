"""
GUI共通ユーティリティ
"""
import tkinter as tk

# グローバル変数：メインアプリのインスタンス
_main_app_instance = None

def set_main_app(app):
    """メインアプリのインスタンスを設定"""
    global _main_app_instance
    _main_app_instance = app

def log_to_gui(message):
    """GUIログエリアにメッセージを出力するグローバル関数"""
    if _main_app_instance:
        _main_app_instance.log_message(message)
    else:
        print(message)  # フォールバック

def show_error(parent, title, message):
    """エラーダイアログ表示"""
    import tkinter.messagebox as msgbox
    msgbox.showerror(title, message, parent=parent)

def show_info(parent, title, message):
    """情報ダイアログ表示"""
    import tkinter.messagebox as msgbox
    msgbox.showinfo(title, message, parent=parent)

def show_confirm(parent, title, message):
    """確認ダイアログ表示"""
    import tkinter.messagebox as msgbox
    return msgbox.askyesno(title, message, parent=parent)