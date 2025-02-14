from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QHBoxLayout,
)
from PyQt5.QtCore import pyqtSignal


class YoloSettingsDialog(QDialog):
    detection_settings_changed = pyqtSignal(dict)

    def __init__(self, detection_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YOLO檢測設定")
        self.detection_settings = dict(detection_settings)  # make a copy
        self.init_ui()

    def init_ui(self):
        form_layout = QFormLayout()

        # Detection enable checkbox
        self.enable_checkbox = QCheckBox("啟用檢測")
        self.enable_checkbox.setChecked(self.detection_settings.get("enabled", False))
        form_layout.addRow("檢測啟用:", self.enable_checkbox)

        # Model selection: QComboBox and a browse button
        self.model_combo = QComboBox()
        default_models = [
            "yolov8n.pt",
            "yolov8s.pt",
            "yolov8m.pt",
            "yolov8l.pt",
            "yolov8x.pt",
            "自選模型",
        ]
        self.model_combo.addItems(default_models)
        current_model = self.detection_settings.get("model", "yolov8n.pt")
        if current_model not in default_models:
            self.model_combo.addItem(current_model)
        self.model_combo.setCurrentText(current_model)

        self.choose_model_btn = QPushButton("選擇模型")
        self.choose_model_btn.clicked.connect(self.choose_model_file)
        hbox_model = QHBoxLayout()
        hbox_model.addWidget(self.model_combo)
        hbox_model.addWidget(self.choose_model_btn)
        form_layout.addRow("模型:", hbox_model)

        # Detection mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["拼接圖片檢測", "單張圖片檢測"])
        current_mode = self.detection_settings.get("mode", "拼接圖片檢測")
        self.mode_combo.setCurrentText(current_mode)
        form_layout.addRow("檢測方式:", self.mode_combo)

        # Action buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("儲存")
        save_btn.clicked.connect(self.on_save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        form_layout.addRow(btn_layout)

        self.setLayout(form_layout)

    def choose_model_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇 YOLO 模型檔案",
            "",
            "PyTorch Model Files (*.pt);;All Files (*)",
        )
        if file_path:
            if self.model_combo.findText(file_path) == -1:
                self.model_combo.addItem(file_path)
            self.model_combo.setCurrentText(file_path)

    def on_save(self):
        self.detection_settings["enabled"] = self.enable_checkbox.isChecked()
        self.detection_settings["model"] = self.model_combo.currentText()
        self.detection_settings["mode"] = self.mode_combo.currentText()
        self.detection_settings_changed.emit(self.detection_settings)
        self.accept()
