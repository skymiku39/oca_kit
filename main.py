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

    # 加載 CameraCapture.json 的設定
    camera_capture_path = "C:/github/oca_kit/CameraCapture.json"
    camera_capture_data = load_settings(camera_capture_path)

    # 加載 中間測試.json 的設定
    intermediate_test_path = "C:/github/oca_kit/中間測試.json"
    intermediate_test_data = load_settings(intermediate_test_path)

    # 如果有加載到資料，則設置到 MainWindow
    if camera_capture_data:
        win.set_camera_capture_data(camera_capture_data)  # 設置相機捕捉資料

    if intermediate_test_data:
        win.set_intermediate_test_data(intermediate_test_data)  # 設置中間測試資料

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
