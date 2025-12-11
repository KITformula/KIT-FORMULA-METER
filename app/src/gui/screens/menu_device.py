import time
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QListWidget, QWidget

class DeviceMenuScreen(QWidget):
    requestOpenGoPro = pyqtSignal()
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("DEVICES", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: #0FF; margin-bottom: 10px;"))
        
        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget { font-size: 40px; background-color: #222; color: white; border: 2px solid #555; } 
            QListWidget::item { padding: 20px; }
            QListWidget::item:selected { background-color: #008B8B; border: 2px solid #0FF; }
        """)
        self.list.addItems(["1. GoPro Control >", "2. << BACK"])
        self.list.setCurrentRow(0)
        self.layout.addWidget(self.list)
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def handle_input(self, i):
        row = self.list.currentRow()
        if i == "CW": self.list.setCurrentRow(0 if row >= 1 else row + 1); return True
        elif i == "CCW": self.list.setCurrentRow(1 if row <= 0 else row - 1); return True
        elif i == "ENTER":
            if row == 0: self.requestOpenGoPro.emit()
            elif row == 1: self.requestBack.emit()
            return True
        return False

# --- Sub Screen ---
class GoProMenuScreen(QWidget):
    requestConnect = pyqtSignal()
    requestDisconnect = pyqtSignal()
    requestRecStart = pyqtSignal()
    requestRecStop = pyqtSignal()
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.shown_timestamp = 0.0
        self.layout.addWidget(QLabel("GoPro Control", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: #0FF;"))
        
        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget { font-size: 40px; background-color: #222; color: white; } 
            QListWidget::item { padding: 20px; }
            QListWidget::item:selected { background-color: #008B8B; border: 2px solid #0FF; }
        """)
        self.list.addItems(["1. Connect / Retry", "2. Disconnect", "3. Record START", "4. Record STOP", "5. << BACK"])
        self.list.setCurrentRow(0)
        self.layout.addWidget(self.list)
        
        self.status = QLabel("Status: Not Connected", alignment=Qt.AlignCenter, styleSheet="font-size: 20px; color: #AAA; border-top: 1px solid #555;")
        self.bat = QLabel("Battery: --%", alignment=Qt.AlignCenter, styleSheet="font-size: 24px; font-weight: bold; color: #AAA;")
        self.layout.addWidget(self.status); self.layout.addWidget(self.bat)
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def showEvent(self, e): self.shown_timestamp = time.time(); super().showEvent(e)
    def update_status(self, t): 
        c = "#0F0" if "Connect" in t or "Rec" in t or "Ready" in t else "#F00" if "Error" in t else "#FF0"
        self.status.setText(f"Status: {t}"); self.status.setStyleSheet(f"font-size: 20px; color: {c}; border-top: 1px solid #555;")
    def update_battery(self, v):
        c = "#0F0" if v > 50 else "#FF0" if v > 20 else "#F00"
        self.bat.setText(f"Battery: {v}%"); self.bat.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {c};")

    def handle_input(self, i):
        if time.time() - self.shown_timestamp < 0.5: return True
        row = self.list.currentRow()
        if i == "CW": self.list.setCurrentRow(0 if row >= 4 else row + 1); return True
        elif i == "CCW": self.list.setCurrentRow(4 if row <= 0 else row - 1); return True
        elif i == "ENTER":
            if row == 0: self.requestConnect.emit()
            elif row == 1: self.update_status("Disconnecting..."); self.requestDisconnect.emit()
            elif row == 2: self.requestRecStart.emit()
            elif row == 3: self.requestRecStop.emit()
            elif row == 4: self.requestBack.emit()
            return True
        return False