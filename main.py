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

    settings_changed = pyqtSignal()  # 新增此行

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
        save_btn.clicked.connect(self.on_save)
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

    def on_save(self):
        self.settings_changed.emit()  # 發出信號
        self.accept()

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
    以 QDockWidget 做為側邊欄，內含:
    - car/parking/plate 的 CheckBox (顯示/不顯示)
    - 一般狀態和觸發狀態的顏色設定按鈕
    外部可以透過 signals 來知道使用者是否切換顯示/顏色
    """

    label_config_changed = pyqtSignal()  # 通知主視窗重繪

    def __init__(self, parent=None):
        super().__init__("標籤顯示設定", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # 預設顯示狀態
        self.label_states = {
            "car": {
                "visible": True,
                "normal_color": (0, 255, 0),
                "trigger_color": (255, 0, 0),
            },
            "parking": {
                "visible": True,
                "normal_color": (255, 255, 0),
                "trigger_color": (255, 0, 255),
            },
            "plate": {
                "visible": True,
                "normal_color": (0, 255, 255),
                "trigger_color": (0, 0, 255),
            },
        }

        # 建立介面
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 為每種標籤類型建立控制項
        for label_type in ["car", "parking", "plate"]:
            # 群組標題
            layout.addWidget(QLabel(f"=== {label_type} ==="))

            # 顯示控制
            check = QCheckBox(f"顯示 {label_type}")
            check.setChecked(True)
            check.clicked.connect(
                lambda checked, lt=label_type: self.on_visibility_changed(lt, checked)
            )
            layout.addWidget(check)

            # 一般顏色
            normal_btn = QPushButton(f"{label_type} 一般顏色")
            normal_btn.clicked.connect(
                lambda _, lt=label_type: self.on_color_button_clicked(lt, "normal")
            )
            layout.addWidget(normal_btn)

            # 觸發顏色
            trigger_btn = QPushButton(f"{label_type} 觸發顏色")
            trigger_btn.clicked.connect(
                lambda _, lt=label_type: self.on_color_button_clicked(lt, "trigger")
            )
            layout.addWidget(trigger_btn)

            # 加入間隔
            layout.addSpacing(10)

        layout.addStretch()
        widget.setLayout(layout)
        self.setWidget(widget)

    def on_visibility_changed(self, label_type, checked):
        """當標籤顯示狀態改變時"""
        self.label_states[label_type]["visible"] = checked
        self.label_config_changed.emit()

    def on_color_button_clicked(self, label_type, color_type):
        """當顏色按鈕被點擊時"""
        current_color = self.label_states[label_type][f"{color_type}_color"]
        initial_qcolor = QColor(current_color[2], current_color[1], current_color[0])

        color = QColorDialog.getColor(
            initial_qcolor, self.widget(), f"選擇 {label_type} {color_type} 顏色"
        )

        if color.isValid():
            self.label_states[label_type][f"{color_type}_color"] = (
                color.blue(),
                color.green(),
                color.red(),
            )
            self.label_config_changed.emit()

    def get_label_color(self, label_type, is_trigger=False):
        """獲取指定標籤類型的當前顏色"""
        if not self.label_states[label_type]["visible"]:
            return (0, 0, 0)  # 如果不可見，返回黑色

        color_type = "trigger_color" if is_trigger else "normal_color"
        return self.label_states[label_type][color_type]

    def save_settings(self, settings):
        for label_type in self.label_states:
            settings.setValue(
                f"{label_type}/visible", self.label_states[label_type]["visible"]
            )
            settings.setValue(
                f"{label_type}/normal_color",
                self.label_states[label_type]["normal_color"],
            )
            settings.setValue(
                f"{label_type}/trigger_color",
                self.label_states[label_type]["trigger_color"],
            )

    def load_settings(self, settings):
        for label_type in self.label_states:
            self.label_states[label_type]["visible"] = settings.value(
                f"{label_type}/visible", True, type=bool
            )
            self.label_states[label_type]["normal_color"] = settings.value(
                f"{label_type}/normal_color", (0, 255, 0), type=tuple
            )
            self.label_states[label_type]["trigger_color"] = settings.value(
                f"{label_type}/trigger_color", (255, 0, 0), type=tuple
            )


# =============================================================================
# MainWindow：只顯示單一 2×2 拼接影像，Side Panel 管理 label
# =============================================================================
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

        # 添加到面板
        panel.addWidget(self.start_btn)
        panel.addWidget(self.stop_btn)
        panel.addWidget(QLabel("畫面比例:"))
        panel.addWidget(self.aspect_ratio_combo)
        panel.addWidget(QLabel("解析度:"))
        panel.addWidget(self.resolution_combo)
        panel.addWidget(self.rotation_check)
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
                if label_type in ["car", "parking", "plate"]:
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
        except Exception as e:
            print(f"draw_label_car_polygon error: {e}")

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
        s.sync()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
