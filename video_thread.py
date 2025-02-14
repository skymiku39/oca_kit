import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal


class VideoThread(QThread):
    frame_signal = pyqtSignal(np.ndarray, int)  # (frame, cam_id)
    error_signal = pyqtSignal(str, int)  # (error_msg, cam_id)

    def __init__(self, rtsp_url, camera_id, parent=None):
        super().__init__(parent)
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self._running = True

    def run(self):
        while self._running:
            cap = cv2.VideoCapture(self.rtsp_url)
            if not cap.isOpened():
                self.error_signal.emit(f"無法開啟來源：{self.rtsp_url}", self.camera_id)
                return

            while self._running:
                ret, frame = cap.read()
                if not ret:
                    self.error_signal.emit(
                        "讀取畫面失敗，嘗試重新連接...", self.camera_id
                    )
                    cap.release()
                    QThread.sleep(2)  # 暫停2秒後重新連接
                    break
                self.frame_signal.emit(frame, self.camera_id)
        cap.release()

    def stop(self):
        self._running = False
        self.wait()
