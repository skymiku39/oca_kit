import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow
import os
import json


def load_settings(file_path):
    """Load settings from a JSON file."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    else:
        print(f"Warning: {file_path} does not exist. Proceeding with default settings.")
        return None  # Return None if the file does not exist


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()

    # Load settings from CameraCapture.json
    camera_capture_path = "C:/github/oca_kit/CameraCapture.json"
    camera_capture_data = load_settings(camera_capture_path)

    # Load settings from 中間測試.json
    intermediate_test_path = "C:/github/oca_kit/中間測試.json"
    intermediate_test_data = load_settings(intermediate_test_path)

    # If you have logic to set the loaded data into the MainWindow, do it here
    if camera_capture_data:
        win.set_camera_capture_data(camera_capture_data)  # Example method to set data

    if intermediate_test_data:
        win.set_intermediate_test_data(
            intermediate_test_data
        )  # Example method to set data

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
