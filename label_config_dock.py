from PyQt5.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QColorDialog,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor


class LabelConfigDock(QDockWidget):
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
