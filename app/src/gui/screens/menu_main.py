from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QListWidget, QWidget


class SettingsScreen(QWidget):
    requestOpenRaceMenu = pyqtSignal()
    requestOpenMachineMenu = pyqtSignal()
    requestOpenDeviceMenu = pyqtSignal()
    requestOpenInfoMenu = pyqtSignal()
    requestExit = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()

        title = QLabel("SETTINGS MENU")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 32px; font-weight: bold; color: yellow; margin-bottom: 10px;"
        )
        self.layout.addWidget(title)

        self.list_widget = QListWidget()
        # フォントサイズ40px, パディング20px
        self.list_widget.setStyleSheet("""
            QListWidget {
                font-size: 40px;
                background-color: #222;
                color: white;
                border: 2px solid #555;
            }
            QListWidget::item {
                padding: 20px;
            }
            QListWidget::item:selected {
                background-color: #00A;
                color: white;
                border: 2px solid yellow;
            }
        """)

        self.items = [
            "1. RACE SETUP      >",
            "2. MACHINE SETUP   >",
            "3. DEVICES         >",
            "4. INFO / LOG      >",
            "5. EXIT",
        ]
        self.list_widget.addItems(self.items)
        self.list_widget.setCurrentRow(0)

        self.layout.addWidget(self.list_widget)
        self.setLayout(self.layout)

        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#333"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def handle_input(self, input_type: str) -> bool:
        current_row = self.list_widget.currentRow()

        if input_type == "CW":
            if current_row < len(self.items) - 1:
                self.list_widget.setCurrentRow(current_row + 1)
            else:
                self.list_widget.setCurrentRow(0)
            return True

        elif input_type == "CCW":
            if current_row > 0:
                self.list_widget.setCurrentRow(current_row - 1)
            else:
                self.list_widget.setCurrentRow(len(self.items) - 1)
            return True

        elif input_type == "ENTER":
            if current_row == 0:
                self.requestOpenRaceMenu.emit()
            elif current_row == 1:
                self.requestOpenMachineMenu.emit()
            elif current_row == 2:
                self.requestOpenDeviceMenu.emit()
            elif current_row == 3:
                self.requestOpenInfoMenu.emit()
            elif current_row == 4:
                self.requestExit.emit()
            return True

        return False