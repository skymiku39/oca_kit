import sys
from PyQt5.QtWidgets import (
    QMainWindow,
    QApplication,
    QMessageBox,
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QCheckBox,
    QAction,
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QImage, QPixmap, QColor
from ultralytics import YOLO
from video_thread import VideoThread
from camera_settings_dialog import CameraSettingsDialog
from label_config_dock import LabelConfigDock
from yolo_settings_dialog import YoloSettingsDialog
import numpy as np
import cv2
import json

COLORS = [
    (255, 0, 0),  # Red
    (0, 255, 0),  # Green
    (0, 0, 255),  # Blue
    (255, 255, 0),  # Yellow
    (255, 0, 255),  # Magenta
    (0, 255, 255),  # Cyan
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多攝影機 2×2 拼接監控系統")

        # 預設攝影機設定
        self.default_configs = {
            1: {
                "ip": "192.168.60.102",
                "port": "554",
                "user": "admin",
                "pwd": "",
                "enabled": True,
                "label_path": "",
            },
            2: {
                "ip": "192.168.60.102",
                "port": "554",
                "user": "admin",
                "pwd": "",
                "enabled": True,
                "label_path": "",
            },
            3: {
                "ip": "192.168.60.102",
                "port": "554",
                "user": "admin",
                "pwd": "",
                "enabled": True,
                "label_path": "",
            },
            4: {
                "ip": "192.168.60.102",
                "port": "554",
                "user": "admin",
                "pwd": "",
                "enabled": True,
                "label_path": "",
            },
        }

        # 集中管理顯示設定
        self.display_settings = {
            "aspect_ratio": "16:9",
            "resolution": "1080p",
            "rotation": False,
            "resolutions": {
                "1080p": {"16:9": (1920, 1080), "9:16": (1080, 1920)},
                "720p": {"16:9": (1280, 720), "9:16": (720, 1280)},
            },
        }

        self.settings = QSettings("MyCompany", "MyCameraApp")
        self.camera_configs = self.load_settings()

        self.threads = {}
        self.latest_frames = {}
        self.composited_image_bgr = None

        self.label_config_dock = LabelConfigDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.label_config_dock)
        self.label_config_dock.label_config_changed.connect(self.update_composite)

        self.detection_enabled = False
        self.yolo_detector = None
        self.detection_settings = {"enabled": False, "model": "yolov8n.pt"}

        self.init_ui()

    def init_ui(self):
        # 建立主要控制面板
        control_panel = self.create_control_panel()

        # 建立顯示區域
        self.display_label = QLabel()
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setStyleSheet("background-color: black;")

        # 主要布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.addLayout(control_panel)
        main_layout.addWidget(self.display_label)

        self.setCentralWidget(central_widget)
        self.resize(1200, 800)

        # 建立選單
        self.create_menu()

        self.label_config_dock.load_settings(
            self.settings
        )  # Load label colors/settings

    def create_menu(self):
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("設定")

        camera_settings_action = QAction("攝影機設定", self)
        camera_settings_action.triggered.connect(self.open_camera_settings_dialog)
        settings_menu.addAction(camera_settings_action)

    def create_control_panel(self):
        panel = QHBoxLayout()

        # 串流控制
        self.start_btn = QPushButton("開始串流")
        self.stop_btn = QPushButton("停止串流")
        self.start_btn.clicked.connect(self.start_streams)
        self.stop_btn.clicked.connect(self.stop_streams)

        # 顯示設定
        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItems(["16:9", "9:16"])
        self.aspect_ratio_combo.setCurrentText(self.display_settings["aspect_ratio"])
        self.aspect_ratio_combo.currentTextChanged.connect(
            self.on_display_settings_changed
        )

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1080p", "720p"])
        self.resolution_combo.setCurrentText(self.display_settings["resolution"])
        self.resolution_combo.currentTextChanged.connect(
            self.on_display_settings_changed
        )

        self.rotation_check = QCheckBox("旋轉")
        self.rotation_check.setChecked(self.display_settings["rotation"])
        self.rotation_check.stateChanged.connect(self.on_display_settings_changed)

        # YOLO Detection control (new independent dialog)
        self.detection_button = QPushButton("YOLO檢測設定")
        self.detection_button.clicked.connect(self.open_yolo_settings_dialog)

        # Adding widgets to the panel
        panel.addWidget(self.start_btn)
        panel.addWidget(self.stop_btn)
        panel.addWidget(QLabel("畫面比例:"))
        panel.addWidget(self.aspect_ratio_combo)
        panel.addWidget(QLabel("解析度:"))
        panel.addWidget(self.resolution_combo)
        panel.addWidget(self.rotation_check)
        panel.addWidget(self.detection_button)
        panel.addStretch()

        return panel

    def on_display_settings_changed(self):
        """當顯示設定改變時更新"""
        self.display_settings.update(
            {
                "aspect_ratio": self.aspect_ratio_combo.currentText(),
                "resolution": self.resolution_combo.currentText(),
                "rotation": self.rotation_check.isChecked(),
            }
        )
        self.update_composite()

    def start_streams(self):
        """開始所有已啟用攝影機的串流"""
        for cam_id, config in self.camera_configs.items():
            if config["enabled"]:
                rtsp_url = f"rtsp://{config['user']}:{config['pwd']}@{config['ip']}:{config['port']}/"
                thread = VideoThread(rtsp_url, cam_id)
                thread.frame_signal.connect(self.update_frame)
                thread.error_signal.connect(self.handle_error)
                thread.start()
                self.threads[cam_id] = thread

    def stop_streams(self):
        """停止所有串流執行緒"""
        for thread in self.threads.values():
            thread.stop()
        self.threads.clear()

    def update_frame(self, frame, cam_id):
        """接收來自攝影機的影格信號"""
        self.latest_frames[cam_id] = frame
        self.update_composite()

    def update_composite(self):
        """更新拼接影像"""
        if not self.latest_frames:
            return

        # 獲取目標尺寸
        aspect = self.display_settings["aspect_ratio"]
        res = self.display_settings["resolution"]
        final_w, final_h = self.display_settings["resolutions"][res][aspect]

        # 建立拼接畫布
        cell_w, cell_h = final_w // 2, final_h // 2
        collage = np.zeros((final_h, final_w, 3), dtype=np.uint8)

        try:
            for i, cam_id in enumerate([1, 2, 3, 4]):
                r, c = divmod(i, 2)
                y0, x0 = r * cell_h, c * cell_w

                frame = self.get_camera_frame(cam_id, cell_w, cell_h)
                if frame is not None:
                    # 畫標籤
                    if self.camera_configs[cam_id]["label_path"]:
                        label_path = self.camera_configs[cam_id]["label_path"]
                        self.draw_label_car_polygon(frame, label_path)

                    collage[y0 : y0 + cell_h, x0 : x0 + cell_w] = frame

            if self.display_settings["rotation"]:
                collage = cv2.rotate(collage, cv2.ROTATE_90_CLOCKWISE)

            self.composited_image_bgr = collage
            self.update_label_resized()

        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"更新影像時發生錯誤: {str(e)}")

    def get_camera_frame(self, cam_id, cell_w, cell_h):
        """獲取單一攝影機的影格"""
        if not self.camera_configs[cam_id]["enabled"]:
            return self.create_offline_frame(f"Camera {cam_id} 已停用", cell_w, cell_h)

        if cam_id not in self.latest_frames:
            return self.create_offline_frame(f"Camera {cam_id} 無訊號", cell_w, cell_h)

        frame = self.latest_frames[cam_id]
        return self.fit_frame_to_cell(frame, cell_w, cell_h)

    def create_offline_frame(self, message, width, height):
        """創建離線狀態的影格"""
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(
            frame,
            message,
            (10, height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
        )
        return frame

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

    def draw_label_car_polygon(self, image_bgr, label_json_path):
        """
        在縮放後影像上畫出所有類型的標籤多邊形
        根據 side panel 的設定決定是否顯示及顏色
        """
        h, w = image_bgr.shape[:2]
        try:
            with open(label_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for obj in data.get("labels", []):
                label_type = obj.get("label_type")
                # Check if the label is visible
                if label_type in ["car", "parking", "plate"]:
                    visible = self.label_config_dock.label_states[label_type]["visible"]
                    if not visible:
                        continue  # Skip drawing if not visible

                    # 獲取顏色（目前都使用一般狀態的顏色）
                    color = self.label_config_dock.get_label_color(label_type)

                    pts_norm = obj.get("points_normalized", [])
                    if pts_norm:
                        polygon = []
                        for nx, ny in pts_norm:
                            px = int(nx * w)
                            py = int(ny * h)
                            polygon.append((px, py))
                        if polygon:
                            poly_np = np.array([polygon], dtype=np.int32)
                            cv2.polylines(image_bgr, poly_np, True, color, 2)
        except FileNotFoundError as e:
            print(f"draw_label_car_polygon error: {e}")
            return image_bgr  # Return the original image without any modifications
        except Exception as e:
            print(f"draw_label_car_polygon unexpected error: {e}")
            return image_bgr  # Return the original image without any modifications

    def update_label_resized(self):
        """將拼接影像轉換為 QPixmap 並顯示在 QLabel 上"""
        if self.composited_image_bgr is not None:
            # 轉換 BGR 到 RGB
            image_rgb = cv2.cvtColor(self.composited_image_bgr, cv2.COLOR_BGR2RGB)
            height, width, channel = image_rgb.shape
            bytes_per_line = 3 * width
            q_img = QImage(
                image_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888
            )
            pixmap = QPixmap.fromImage(q_img)
            self.display_label.setPixmap(
                pixmap.scaled(
                    self.display_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

    # ============ 視窗關閉前 ============
    def closeEvent(self, event):
        self.stop_streams()
        self.save_settings()
        super().closeEvent(event)

    # ============ 錯誤處理 ============
    def handle_error(self, msg, cam_id):
        QMessageBox.warning(self, "攝影機錯誤", f"Camera {cam_id} 錯誤: {msg}")

    # ============ 設定存取 ============
    def open_camera_settings_dialog(self):
        dlg = CameraSettingsDialog(self.camera_configs, self)
        dlg.settings_changed.connect(self.update_composite)  # 新增此行
        if dlg.exec_():
            self.camera_configs = dlg.get_configs()
            self.save_settings()
            QMessageBox.information(self, "訊息", "已更新攝影機設定")
            self.stop_streams()
            self.start_streams()
            self.update_composite()  # 新增此行以即時更新畫面

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
        self.label_config_dock.save_settings(
            self.settings
        )  # Save label colors/settings
        s.sync()

    def open_yolo_settings_dialog(self):
        dlg = YoloSettingsDialog(self.detection_settings, self)
        dlg.detection_settings_changed.connect(self.on_yolo_settings_changed)
        dlg.exec_()

    def on_yolo_settings_changed(self, new_settings):
        self.detection_settings = new_settings
        self.detection_enabled = new_settings.get("enabled", False)
        if self.detection_enabled:
            self.load_yolo_model(new_settings.get("model", "yolov8n.pt"))
        else:
            self.yolo_detector = None
        self.update_composite()

    def load_yolo_model(self, model_path):
        try:
            self.yolo_detector = YOLO(model_path)
        except Exception as e:
            QMessageBox.warning(
                self, "YOLO Model Error", f"Failed to load YOLO model: {str(e)}"
            )
            self.yolo_detector = None
            self.detection_enabled = False

    def apply_detection(self, frame):
        """Apply YOLO detection on frame and draw bounding boxes"""
        try:
            results = self.yolo_detector(frame)
            if len(results) == 0:
                return frame
            result = results[0]
            if result.boxes is None:
                return frame
            # Convert detections to numpy array with shape [N,6] (x1, y1, x2, y2, conf, cls)
            dets = result.boxes.data.cpu().numpy()
            for det in dets:
                x1, y1, x2, y2, conf, cls_id = det
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                if hasattr(self.yolo_detector, "names"):
                    label = self.yolo_detector.names[int(cls_id)]
                else:
                    label = str(int(cls_id))
                color = COLORS[int(cls_id) % len(COLORS)]
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    f"{label} {conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )
            return frame
        except Exception as e:
            print(f"Detection error: {e}")
            return frame

    def set_camera_capture_data(self, data):
        """Set camera capture data from loaded settings."""
        # Assuming data is a dictionary with camera settings
        # You can implement the logic to apply these settings
        print("Camera capture data set:", data)
        # Example: self.camera_settings = data

    def set_intermediate_test_data(self, data):
        """Set intermediate test data from loaded settings."""
        # Assuming data is a dictionary with intermediate test settings
        print("Intermediate test data set:", data)
        # Example: self.intermediate_test_settings = data
