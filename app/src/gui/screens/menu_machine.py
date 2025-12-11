from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QListWidget, QWidget

class MachineMenuScreen(QWidget):
    requestOpenLSD = pyqtSignal()
    requestOpenFuel = pyqtSignal()
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("MACHINE SETUP", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: orange; margin-bottom: 10px;"))
        
        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget { font-size: 40px; background-color: #222; color: white; border: 2px solid #555; } 
            QListWidget::item { padding: 20px; }
            QListWidget::item:selected { background-color: #8B4500; border: 2px solid orange; }
        """)
        self.list.addItems(["1. LSD Adjustment >", "2. Fuel Reset >", "3. << BACK"])
        self.list.setCurrentRow(0)
        self.layout.addWidget(self.list)
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def handle_input(self, i):
        row = self.list.currentRow()
        if i == "CW": self.list.setCurrentRow(0 if row >= 2 else row + 1); return True
        elif i == "CCW": self.list.setCurrentRow(2 if row <= 0 else row - 1); return True
        elif i == "ENTER":
            if row == 0: self.requestOpenLSD.emit()
            elif row == 1: self.requestOpenFuel.emit()
            elif row == 2: self.requestBack.emit()
            return True
        return False

# --- Sub Screens ---

class LSDMenuScreen(QWidget):
    lsdLevelChanged = pyqtSignal(int)
    requestBack = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.level = 1
        self.layout.addWidget(QLabel("LSD ADJUSTMENT", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: #F0F;"))
        self.lbl = QLabel(f"LEVEL: {self.level}", alignment=Qt.AlignCenter, styleSheet="font-size: 80px; font-weight: bold; color: white;")
        self.layout.addWidget(self.lbl)
        self.layout.addWidget(QLabel("Rotary: Adjust / Push: BACK", alignment=Qt.AlignCenter, styleSheet="font-size: 20px; color: #AAA;"))
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def handle_input(self, i):
        if i == "CW":
            if self.level < 5: self.level += 1; self.lbl.setText(f"LEVEL: {self.level}"); self.lsdLevelChanged.emit(self.level)
            return True
        elif i == "CCW":
            if self.level > 1: self.level -= 1; self.lbl.setText(f"LEVEL: {self.level}"); self.lsdLevelChanged.emit(self.level)
            return True
        elif i == "ENTER": self.requestBack.emit(); return True
        return False

class FuelResetScreen(QWidget):
    requestReset = pyqtSignal()
    requestBack = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("FUEL RESET", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: orange;"))
        self.val = QLabel("Current: -- %", alignment=Qt.AlignCenter, styleSheet="font-size: 60px; font-weight: bold; color: white;")
        self.layout.addWidget(self.val)
        self.msg = QLabel("RESET COMPLETE", alignment=Qt.AlignCenter, styleSheet="font-size: 40px; color: #0F0; background: rgba(0,0,0,150);"); self.msg.hide()
        self.layout.addWidget(self.msg)
        self.layout.addWidget(QLabel("Push: RESET 100%", alignment=Qt.AlignCenter, styleSheet="font-size: 20px; color: #AAA;"))
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def update_fuel(self, p): self.val.setText(f"Current: {int(p)} %")
    def handle_input(self, i):
        if self.msg.isVisible(): return True
        if i == "ENTER":
            self.requestReset.emit(); self.msg.show()
            QTimer.singleShot(1500, lambda: [self.msg.hide(), self.requestBack.emit()])
            return True
        elif i in ["CW", "CCW"]: self.requestBack.emit(); return True
        return False