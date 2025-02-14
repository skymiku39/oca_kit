import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow
import os
import json


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()

    # 檢查 CameraCapture.json 檔案是否存在
    camera_capture_path = "C:/github/oca_kit/CameraCapture.json"
    if not os.path.exists(camera_capture_path):
        with open(camera_capture_path, "w") as f:
            json.dump({}, f)  # 創建一個空的 JSON 物件

    # 檢查 中間測試.json 檔案是否存在
    intermediate_test_path = "C:/github/oca_kit/中間測試.json"
    if not os.path.exists(intermediate_test_path):
        with open(intermediate_test_path, "w") as f:
            json.dump({}, f)  # 創建一個空的 JSON 物件

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
