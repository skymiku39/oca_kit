import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow
import os
import json

"""
主程式入口
此程式負責啟動應用程式，並加載必要的設定檔案。
"""


def load_settings(file_path):
    """從 JSON 檔案加載設定。"""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    else:
        print(f"警告: {file_path} 不存在。將使用預設設定。")
        return None  # 如果檔案不存在，返回 None


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
