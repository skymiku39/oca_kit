import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

"""
視頻線程類別
此類別負責從攝影機或視頻源捕獲影像，並在獨立線程中處理影像數據。
它會發送捕獲的影像幀和錯誤信息到主界面。
"""


class VideoThread(QThread):
    frame_signal = pyqtSignal(np.ndarray, int)  # (frame, cam_id)
    error_signal = pyqtSignal(str, int)  # (error_msg, cam_id)

    def __init__(self, rtsp_url, camera_id, parent=None):
        super().__init__(parent)
        self.rtsp_url = rtsp_url  # RTSP 來源 URL
        self.camera_id = camera_id  # 攝影機 ID
        self._running = True  # 控制線程運行的標誌

    def run(self):
        """執行線程，捕獲視頻幀。"""
        while self._running:
            cap = cv2.VideoCapture(self.rtsp_url)  # 嘗試打開視頻來源
            if not cap.isOpened():
                self.error_signal.emit(f"無法開啟來源：{self.rtsp_url}", self.camera_id)
                return

            while self._running:
                ret, frame = cap.read()  # 讀取幀
                if not ret:
                    self.error_signal.emit(
                        "讀取畫面失敗，嘗試重新連接...", self.camera_id
                    )
                    cap.release()  # 釋放資源
                    QThread.sleep(2)  # 暫停2秒後重新連接
                    break
                self.frame_signal.emit(frame, self.camera_id)  # 發送捕獲的幀
        cap.release()  # 確保釋放資源

    def stop(self):
        """停止視頻捕獲線程。"""
        self._running = False  # 設置運行標誌為 False
        self.wait()  # 等待線程結束
