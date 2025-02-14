from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QHBoxLayout,
)
from PyQt5.QtCore import pyqtSignal


class CameraSettingsDialog(QDialog):
    settings_changed = pyqtSignal()

    def __init__(self, configs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("攝影機設定")
        self.configs = {cam: dict(configs[cam]) for cam in configs}
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
        self.settings_changed.emit()
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
