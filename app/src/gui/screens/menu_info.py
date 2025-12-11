from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QListWidget, QWidget

class InfoMenuScreen(QWidget):
    requestOpenMileage = pyqtSignal()
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("INFO / LOG", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: #00BFFF; margin-bottom: 10px;"))
        
        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget { font-size: 40px; background-color: #222; color: white; border: 2px solid #555; } 
            QListWidget::item { padding: 20px; }
            QListWidget::item:selected { background-color: #00008B; border: 2px solid #00BFFF; }
        """)
        self.list.addItems(["1. Mileage Info >", "2. << BACK"])
        self.list.setCurrentRow(0)
        self.layout.addWidget(self.list)
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def handle_input(self, i):
        row = self.list.currentRow()
        if i == "CW": self.list.setCurrentRow(0 if row >= 1 else row + 1); return True
        elif i == "CCW": self.list.setCurrentRow(1 if row <= 0 else row - 1); return True
        elif i == "ENTER":
            if row == 0: self.requestOpenMileage.emit()
            elif row == 1: self.requestBack.emit()
            return True
        return False

# --- Sub Screen ---
class MileageScreen(QWidget):
    requestBack = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("MILEAGE INFO", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: #00BFFF;"))
        self.today = QLabel("Today: --.- km", alignment=Qt.AlignCenter, styleSheet="font-size: 48px; font-weight: bold; color: white;")
        self.total = QLabel("Total: ----.- km", alignment=Qt.AlignCenter, styleSheet="font-size: 48px; font-weight: bold; color: #AAA;")
        self.layout.addWidget(self.today); self.layout.addWidget(self.total)
        self.layout.addWidget(QLabel("Rotary: BACK", alignment=Qt.AlignCenter, styleSheet="font-size: 20px; color: #AAA;"))
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def update_distance(self, d, t): self.today.setText(f"Today: {d:.1f} km"); self.total.setText(f"Total: {t:.1f} km")
    def handle_input(self, i): 
        if i in ["CW", "CCW", "ENTER"]: self.requestBack.emit(); return True
        return False