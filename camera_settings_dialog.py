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

"""
攝影機設定對話框類別
此類別負責顯示和管理攝影機的設定，包括 IP、端口、用戶名、密碼等。
使用者可以在此對話框中修改攝影機的設定並儲存。
"""


class CameraSettingsDialog(QDialog):
    settings_changed = pyqtSignal()  # 當設定改變時發出信號

    def __init__(self, configs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("攝影機設定")
        self.configs = {cam: dict(configs[cam]) for cam in configs}  # 複製攝影機設定
        self.init_ui()  # 初始化用戶界面

    def init_ui(self):
        """初始化用戶界面，創建各種輸入框和按鈕。"""
        form_layout = QFormLayout()
        self.ip_edits = {}
        self.port_edits = {}
        self.user_edits = {}
        self.pwd_edits = {}
        self.enable_checks = {}
        self.label_path_edits = {}

        # 為每個攝影機創建設定輸入框
        for cam_id in [1, 2, 3, 4]:
            ip_edit = QLineEdit(self.configs[cam_id].get("ip", "192.168.60.102"))
            port_edit = QLineEdit(self.configs[cam_id].get("port", "554"))
            user_edit = QLineEdit(self.configs[cam_id].get("user", "admin"))
            pwd_edit = QLineEdit(self.configs[cam_id].get("pwd", ""))
            pwd_edit.setEchoMode(QLineEdit.Password)  # 密碼框隱藏輸入
            en_check = QCheckBox("啟用")
            en_check.setChecked(self.configs[cam_id].get("enabled", True))

            label_edit = QLineEdit(self.configs[cam_id].get("label_path", ""))
            choose_btn = QPushButton("選擇檔案")
            choose_btn.clicked.connect(
                lambda _, cid=cam_id: self.choose_label_path(cid)
            )

            # 將輸入框和按鈕存儲到字典中
            self.ip_edits[cam_id] = ip_edit
            self.port_edits[cam_id] = port_edit
            self.user_edits[cam_id] = user_edit
            self.pwd_edits[cam_id] = pwd_edit
            self.enable_checks[cam_id] = en_check
            self.label_path_edits[cam_id] = label_edit

            # 將輸入框添加到表單佈局中
            form_layout.addRow(f"Camera {cam_id} IP:", ip_edit)
            form_layout.addRow(f"Camera {cam_id} Port:", port_edit)
            form_layout.addRow(f"Camera {cam_id} User:", user_edit)
            form_layout.addRow(f"Camera {cam_id} Pwd:", pwd_edit)
            form_layout.addRow(f"Camera {cam_id} 啟用:", en_check)

            hbox_label = QHBoxLayout()
            hbox_label.addWidget(label_edit)
            hbox_label.addWidget(choose_btn)
            form_layout.addRow(f"Camera {cam_id} Label JSON:", hbox_label)

        # 操作按鈕
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
        """選擇標籤 JSON 檔案的路徑。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"選擇 Camera {cam_id} 的 JSON 檔",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self.label_path_edits[cam_id].setText(file_path)

    def on_save(self):
        """儲存當前設定並發出信號。"""
        self.settings_changed.emit()  # 發出設定改變的信號
        self.accept()  # 關閉對話框

    def get_configs(self):
        """返回當前攝影機設定的字典。"""
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
