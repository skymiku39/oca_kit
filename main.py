import sys
import cv2
import json
import numpy as np
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QRect
from PyQt5.QtGui import QImage, QPixmap, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QDialog,
    QLineEdit,
    QCheckBox,
    QMessageBox,
    QAction,
    QMenuBar,
    QFileDialog,
    QDockWidget,
    QColorDialog,
    QComboBox,
)


# =============================================================================
# VideoThread：單一攝影機讀取執行緒
# =============================================================================
class VideoThread(QThread):
    frame_signal = pyqtSignal(np.ndarray, int)  # (frame, cam_id)
    error_signal = pyqtSignal(str, int)  # (error_msg, cam_id)

    def __init__(self, rtsp_url, camera_id, parent=None):
        super().__init__(parent)
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self._running = True

    def run(self):
        cap = cv2.VideoCapture(self.rtsp_url)
        if not cap.isOpened():
            self.error_signal.emit(f"無法開啟來源：{self.rtsp_url}", self.camera_id)
            return

        while self._running:
            ret, frame = cap.read()
            if not ret:
                self.error_signal.emit("讀取畫面失敗", self.camera_id)
                break
            self.frame_signal.emit(frame, self.camera_id)
        cap.release()

    def stop(self):
        self._running = False
        self.wait()


# =============================================================================
# CameraSettingsDialog：一次設定 4 台攝影機 + label JSON 路徑
# =============================================================================
class CameraSettingsDialog(QDialog):
    """
    configs: {
      1: {"ip":"...", "port":"...", "user":"...", "pwd":"...", "enabled":bool, "label_path":"..."},
      2: {...},
      3: {...},
      4: {...}
    }
    """

    def __init__(self, configs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("攝影機設定")
        self.configs = {cam: dict(configs[cam]) for cam in configs}  # copy
        self.init_ui()

    def init_ui(self):
        form_layout = QFormLayout()
        self.ip_edits = {}
        self.port_edits = {}
        self.user_edits = {}
        self.pwd_edits = {}
        self.enable_checks = {}
        self.label_path_edits = {}

        for cam_id in [1, 2, 3, 4]:
            ip_edit = QLineEdit(self.configs[cam_id].get("ip", "192.168.60.102"))
            port_edit = QLineEdit(self.configs[cam_id].get("port", "554"))
            user_edit = QLineEdit(self.configs[cam_id].get("user", "admin"))
            pwd_edit = QLineEdit(self.configs[cam_id].get("pwd", ""))
            pwd_edit.setEchoMode(QLineEdit.Password)
            en_check = QCheckBox("啟用")
            en_check.setChecked(self.configs[cam_id].get("enabled", True))

            label_edit = QLineEdit(self.configs[cam_id].get("label_path", ""))
            choose_btn = QPushButton("選擇檔案")
            choose_btn.clicked.connect(
                lambda _, cid=cam_id: self.choose_label_path(cid)
            )

            self.ip_edits[cam_id] = ip_edit
            self.port_edits[cam_id] = port_edit
            self.user_edits[cam_id] = user_edit
            self.pwd_edits[cam_id] = pwd_edit
            self.enable_checks[cam_id] = en_check
            self.label_path_edits[cam_id] = label_edit

            form_layout.addRow(f"Camera {cam_id} IP:", ip_edit)
            form_layout.addRow(f"Camera {cam_id} Port:", port_edit)
            form_layout.addRow(f"Camera {cam_id} User:", user_edit)
            form_layout.addRow(f"Camera {cam_id} Pwd:", pwd_edit)
            form_layout.addRow(f"Camera {cam_id} 啟用:", en_check)

            hbox_label = QHBoxLayout()
            hbox_label.addWidget(label_edit)
            hbox_label.addWidget(choose_btn)
            form_layout.addRow(f"Camera {cam_id} Label JSON:", hbox_label)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("儲存")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        form_layout.addRow(btn_layout)

        self.setLayout(form_layout)

    def choose_label_path(self, cam_id):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"選擇 Camera {cam_id} 的 JSON 檔",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self.label_path_edits[cam_id].setText(file_path)

    def get_configs(self):
        new_data = {}
        for cam_id in [1, 2, 3, 4]:
            new_data[cam_id] = {
                "ip": self.ip_edits[cam_id].text().strip(),
                "port": self.port_edits[cam_id].text().strip(),
                "user": self.user_edits[cam_id].text().strip(),
                "pwd": self.pwd_edits[cam_id].text(),
                "enabled": self.enable_checks[cam_id].isChecked(),
                "label_path": self.label_path_edits[cam_id].text().strip(),
            }
        return new_data


# =============================================================================
# LabelConfigDock：側邊欄，用於管理 label_type 的顯示 & 顏色
#   - 本範例只示範「car」
# =============================================================================
class LabelConfigDock(QDockWidget):
    """
    以 QDockWidget 做為側邊欄，內有car的CheckBox(顯示/不顯示)與顏色設定按鈕
    外部可以透過 signals 來知道使用者是否切換顯示/顏色
    """

    label_config_changed = pyqtSignal()  # 通知主視窗重繪

    def __init__(self, parent=None):
        super().__init__("標籤顯示設定", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # 預設 car 顯示/顏色 (BGR or RGB都行, 這裡用BGR, 方便cv2)
        # 不過PyQt顏色通常是RGB, 我們再轉換
        self.car_visible = True
        self.car_color_bgr = (0, 255, 0)  # 綠色

        # 建立介面
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.check_car = QCheckBox("顯示 car")
        self.check_car.setChecked(True)
        self.check_car.clicked.connect(self.on_check_car_changed)
        layout.addWidget(self.check_car)

        self.btn_car_color = QPushButton("car 顏色")
        self.btn_car_color.clicked.connect(self.on_btn_car_color)
        layout.addWidget(self.btn_car_color)

        layout.addStretch()
        widget.setLayout(layout)
        self.setWidget(widget)

    def on_check_car_changed(self):
        self.car_visible = self.check_car.isChecked()
        self.label_config_changed.emit()

    def on_btn_car_color(self):
        # 打開 PyQt 顏色選擇器
        initial_qcolor = QColor(
            self.car_color_bgr[2], self.car_color_bgr[1], self.car_color_bgr[0]
        )
        color = QColorDialog.getColor(initial_qcolor, self.widget(), "選擇 car 顏色")
        if color.isValid():
            # 轉成 BGR
            self.car_color_bgr = (color.blue(), color.green(), color.red())
            self.label_config_changed.emit()


# =============================================================================
# MainWindow：只顯示單一 2×2 拼接影像，Side Panel 管理 label
# =============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多攝影機 2×2 拼接 (視窗可調整+側邊欄)")

        self.settings = QSettings("MyCompany", "MyCameraApp")
        self.default_configs = {
            1: {
                "ip": "192.168.60.102",
                "port": "554",
                "user": "admin",
                "pwd": "56632513",
                "enabled": True,
                "label_path": "",
            },
            2: {
                "ip": "192.168.60.103",
                "port": "554",
                "user": "admin",
                "pwd": "56632513",
                "enabled": True,
                "label_path": "",
            },
            3: {
                "ip": "192.168.60.104",
                "port": "554",
                "user": "admin",
                "pwd": "56632513",
                "enabled": True,
                "label_path": "",
            },
            4: {
                "ip": "192.168.60.105",
                "port": "554",
                "user": "admin",
                "pwd": "56632513",
                "enabled": True,
                "label_path": "",
            },
        }
        self.camera_configs = self.load_settings()

        # 多攝影機 Thread & 最新畫面
        self.threads = {}
        self.latest_frames = {}
        # 內部儲存拼接後(640×480)的「原圖」(BGR)，以便在resizeEvent中做等比例縮放
        self.composited_image_bgr = None

        self.init_ui()

    def init_ui(self):
        # 選單
        menubar = self.menuBar()
        menu = menubar.addMenu("選單")
        action_settings = QAction("攝影機設定", self)
        action_settings.triggered.connect(self.open_camera_settings_dialog)
        menu.addAction(action_settings)

        # 側邊欄( Dock )
        self.dock_label_config = LabelConfigDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_label_config)
        self.dock_label_config.label_config_changed.connect(self.update_composite)

        # 中心Widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # 上方控制按鈕
        top_btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("開始串流")
        self.start_btn.clicked.connect(self.start_streams)
        self.stop_btn = QPushButton("停止串流")
        self.stop_btn.clicked.connect(self.stop_streams)
        top_btn_layout.addWidget(self.start_btn)
        top_btn_layout.addWidget(self.stop_btn)

        # Add dropdown for aspect ratio and resolution
        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItems(["16:9", "9:16"])
        self.aspect_ratio_combo.currentTextChanged.connect(self.update_composite)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1080p", "720p"])
        self.resolution_combo.currentTextChanged.connect(self.update_composite)

        top_btn_layout.addWidget(self.aspect_ratio_combo)
        top_btn_layout.addWidget(self.resolution_combo)

        main_layout.addLayout(top_btn_layout)
        # Add checkbox for rotation
        self.rotation_check = QCheckBox("旋轉")
        self.rotation_check.stateChanged.connect(self.update_composite)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1080p", "720p"])
        self.resolution_combo.currentTextChanged.connect(self.update_composite)

        top_btn_layout.addWidget(self.rotation_check)
        top_btn_layout.addWidget(self.resolution_combo)

        # 下方用QLabel顯示最終拼接圖，但不固定大小
        # 透過 resizeEvent 自行處理縮放
        self.label_composite = QLabel()
        self.label_composite.setStyleSheet("background-color: black; color: white;")
        self.label_composite.setAlignment(Qt.AlignCenter)
        self.label_composite.setText("等待影像...")
        main_layout.addWidget(self.label_composite)

        self.setCentralWidget(central_widget)
        self.resize(900, 600)  # 給個初始大小

    # =============== 視窗大小改變 => 我們重新計算縮放後的圖 ===============
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_label_resized()

    def update_label_resized(self):
        """
        如果 composited_image_bgr 不為 None，就將它等比例縮放
        貼到 label_composite 大小範圍內，空白補黑。
        """
        if self.composited_image_bgr is None:
            return

        label_w = self.label_composite.width()
        label_h = self.label_composite.height()

        # 先以 keep-aspect-ratio 算出縮放後大小
        src_h, src_w = self.composited_image_bgr.shape[:2]
        scale = min(label_w / src_w, label_h / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)

        # 建立一張 label大小 的黑底
        canvas = np.zeros((label_h, label_w, 3), dtype=np.uint8)
        # 將 composited_image_bgr 縮放後貼上
        resized = cv2.resize(self.composited_image_bgr, (new_w, new_h))
        off_x = (label_w - new_w) // 2
        off_y = (label_h - new_h) // 2
        canvas[off_y : off_y + new_h, off_x : off_x + new_w] = resized

        # 轉 QImage 顯示
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        h2, w2, ch = rgb.shape
        qimg = QImage(rgb.data, w2, h2, ch * w2, QImage.Format_RGB888)
        self.label_composite.setPixmap(QPixmap.fromImage(qimg))

    # ============ 串流控制 ============
    def start_streams(self):
        self.stop_streams()
        self.latest_frames = {}
        for cam_id, cfg in self.camera_configs.items():
            if cfg.get("enabled", False):
                url = self.build_rtsp_url(cfg)
                thr = VideoThread(url, cam_id)
                thr.frame_signal.connect(self.update_frame)
                thr.error_signal.connect(self.handle_error)
                thr.start()
                self.threads[cam_id] = thr

    def stop_streams(self):
        for cam_id, thr in self.threads.items():
            thr.stop()
        self.threads.clear()

    def build_rtsp_url(self, cfg):
        ip = cfg["ip"]
        port = cfg["port"]
        user = cfg["user"]
        pwd = cfg["pwd"]
        if user:
            return f"rtsp://{user}:{pwd}@{ip}:{port}/stream"
        else:
            return f"rtsp://{ip}:{port}/stream"

    # ============ 畫面更新、拼接 & 重繪 =============
    def update_frame(self, frame, cam_id):
        self.latest_frames[cam_id] = frame
        self.update_composite()

    def update_composite(self):
        rotation = self.rotation_check.isChecked()
        resolution = self.resolution_combo.currentText()

        if resolution == "1080p":
            if rotation:
                final_w, final_h = (1080, 1920)
            else:
                final_w, final_h = (1920, 1080)
        elif resolution == "720p":
            if rotation:
                final_w, final_h = (720, 1280)
            else:
                final_w, final_h = (1280, 720)
        aspect_ratio = self.aspect_ratio_combo.currentText()
        resolution = self.resolution_combo.currentText()

        if resolution == "1080p":
            if aspect_ratio == "16:9":
                final_w, final_h = (1920, 1080)
            elif aspect_ratio == "9:16":
                final_w, final_h = (1080, 1920)
        elif resolution == "720p":
            if aspect_ratio == "16:9":
                final_w, final_h = (1280, 720)
            elif aspect_ratio == "9:16":
                final_w, final_h = (720, 1280)

        cell_w, cell_h = final_w // 2, final_h // 2
        collage = np.zeros((final_h, final_w, 3), dtype=np.uint8)

        for i, cid in enumerate([1, 2, 3, 4]):
            r = i // 2
            c = i % 2
            y0 = r * cell_h
            x0 = c * cell_w

            if self.camera_configs[cid]["enabled"]:
                if cid in self.latest_frames:
                    frame = self.latest_frames[cid]
                    if aspect_ratio == "9:16":
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    small = self.fit_frame_to_cell(frame, cell_w, cell_h)
                else:
                    small = np.zeros((cell_h, cell_w, 3), dtype=np.uint8)
                    cv2.putText(
                        small,
                        f"Cam {cid}\nNoSig",
                        (10, cell_h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )
            else:
                small = np.zeros((cell_h, cell_w, 3), dtype=np.uint8)
                cv2.putText(
                    small,
                    f"Cam {cid} Off",
                    (10, cell_h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

            collage[y0 : y0 + cell_h, x0 : x0 + cell_w] = small

        self.composited_image_bgr = collage
        self.update_label_resized()

    def fit_frame_to_cell(self, frame_bgr, cell_w, cell_h):
        """
        等比例縮放影像以填滿 cell，保持原始比例。
        """
        h, w = frame_bgr.shape[:2]
        scale = min(cell_w / w, cell_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(frame_bgr, (new_w, new_h))

        # 建立一張 cell 大小的黑底
        canvas = np.zeros((cell_h, cell_w, 3), dtype=np.uint8)
        off_x = (cell_w - new_w) // 2
        off_y = (cell_h - new_h) // 2
        canvas[off_y : off_y + new_h, off_x : off_x + new_w] = resized

        return canvas

    def draw_label_car_polygon(self, image_bgr, label_json_path, color_bgr):
        """
        在縮放後影像 (image_bgr) 上畫car多邊形 (points_normalized)
        若 side panel有關閉, 不畫
        color_bgr 由 side panel決定
        """
        h, w = image_bgr.shape[:2]
        try:
            with open(label_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for obj in data.get("labels", []):
                if obj.get("label_type") == "car":
                    pts_norm = obj.get("points_normalized", [])
                    if pts_norm:  # Only draw if points_normalized is not empty
                        polygon = []
                        for nx, ny in pts_norm:
                            px = int(nx * w)
                            py = int(ny * h)
                            polygon.append((px, py))
                        if polygon:
                            poly_np = np.array([polygon], dtype=np.int32)
                            cv2.polylines(image_bgr, poly_np, True, color_bgr, 2)
        except Exception as e:
            print(f"draw_label_car_polygon error: {e}")

    # ============ 視窗關閉前 ============
    def closeEvent(self, event):
        self.stop_streams()
        self.save_settings()
        super().closeEvent(event)

    # ============ 錯誤處理 ============
    def handle_error(self, msg, cam_id):
        print(f"Camera {cam_id} Error: {msg}")

    # ============ 設定存取 ============
    def open_camera_settings_dialog(self):
        dlg = CameraSettingsDialog(self.camera_configs, self)
        if dlg.exec_():
            self.camera_configs = dlg.get_configs()
            self.save_settings()
            QMessageBox.information(self, "訊息", "已更新攝影機設定")

    def load_settings(self):
        s = self.settings
        configs = {}
        for cid in [1, 2, 3, 4]:
            def_cfg = self.default_configs[cid]
            ip = s.value(f"Camera{cid}/ip", def_cfg["ip"])
            port = s.value(f"Camera{cid}/port", def_cfg["port"])
            user = s.value(f"Camera{cid}/user", def_cfg["user"])
            pwd = s.value(f"Camera{cid}/pwd", def_cfg["pwd"])
            ena = s.value(f"Camera{cid}/enabled", str(def_cfg["enabled"]))
            lblp = s.value(f"Camera{cid}/label_path", def_cfg["label_path"])
            if isinstance(ena, str):
                ena = ena.lower() == "true"

            configs[cid] = {
                "ip": ip,
                "port": port,
                "user": user,
                "pwd": pwd,
                "enabled": ena,
                "label_path": lblp,
            }
        return configs

    def save_settings(self):
        s = self.settings
        for cid in [1, 2, 3, 4]:
            cfg = self.camera_configs[cid]
            s.setValue(f"Camera{cid}/ip", cfg["ip"])
            s.setValue(f"Camera{cid}/port", cfg["port"])
            s.setValue(f"Camera{cid}/user", cfg["user"])
            s.setValue(f"Camera{cid}/pwd", cfg["pwd"])
            s.setValue(f"Camera{cid}/enabled", str(cfg["enabled"]))
            s.setValue(f"Camera{cid}/label_path", cfg["label_path"])
        s.sync()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
