from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QListWidget, QWidget, QGridLayout, QGroupBox

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

# --- Sub Screen: Mileage Info (Modified) ---
class MileageScreen(QWidget):
    requestBack = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        
        # タイトル
        self.layout.addWidget(QLabel("MILEAGE INFO", alignment=Qt.AlignCenter, styleSheet="font-size: 28px; font-weight: bold; color: #00BFFF;"))
        
        # 1. Total & Daily 表示エリア (大きく)
        self.total_group = QGroupBox()
        self.total_group.setStyleSheet("border: none; background-color: #222; border-radius: 5px; margin-bottom: 5px;")
        total_layout = QGridLayout()
        
        self.today_lbl = QLabel("Today: --.- km")
        self.today_lbl.setStyleSheet("font-size: 36px; font-weight: bold; color: #FFF;")
        self.today_lbl.setAlignment(Qt.AlignCenter)
        
        self.total_lbl = QLabel("Total: ----.- km")
        self.total_lbl.setStyleSheet("font-size: 36px; font-weight: bold; color: #AAA;")
        self.total_lbl.setAlignment(Qt.AlignCenter)
        
        total_layout.addWidget(self.today_lbl, 0, 0)
        total_layout.addWidget(self.total_lbl, 1, 0)
        self.total_group.setLayout(total_layout)
        self.layout.addWidget(self.total_group)

        # 2. タイヤごとの表示エリア (グリッドで一覧表示)
        self.tire_group = QGroupBox()
        self.tire_group.setStyleSheet("border: 1px solid #555; background-color: #111; margin-top: 5px;")
        self.tire_layout = QGridLayout()
        
        # 固定ラベルの参照を保持する辞書
        self.tire_labels = {}
        
        # 表示順序の定義
        dry_tires = ["Dry 1", "Dry 2", "Dry 3", "Dry 4", "Dry 5"]
        wet_tires = ["Wet 1", "Wet 2"]
        
        # Dry列 (左)
        for i, name in enumerate(dry_tires):
            lbl = QLabel(f"{name}: 0.0 km")
            lbl.setStyleSheet("font-size: 20px; color: #FFA500;") # オレンジ
            self.tire_layout.addWidget(lbl, i, 0)
            self.tire_labels[name] = lbl
            
        # Wet列 (右)
        for i, name in enumerate(wet_tires):
            lbl = QLabel(f"{name}: 0.0 km")
            lbl.setStyleSheet("font-size: 20px; color: #00BFFF;") # 青
            self.tire_layout.addWidget(lbl, i, 1)
            self.tire_labels[name] = lbl

        self.tire_group.setLayout(self.tire_layout)
        self.layout.addWidget(self.tire_group)

        # フッター
        self.layout.addWidget(QLabel("Rotary: BACK", alignment=Qt.AlignCenter, styleSheet="font-size: 18px; color: #888;"))
        
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def update_distance(self, info: dict):
        """
        info: { 'daily': float, 'total': float, 'tires': { 'Dry 1': float, ... } }
        """
        daily = info.get("daily", 0.0)
        total = info.get("total", 0.0)
        tires = info.get("tires", {})
        
        self.today_lbl.setText(f"Today: {daily:.1f} km")
        self.total_lbl.setText(f"Total: {total:.1f} km")
        
        # タイヤごとの更新
        for name, lbl in self.tire_labels.items():
            dist = tires.get(name, 0.0)
            lbl.setText(f"{name}: {dist:.1f} km")

    def handle_input(self, i): 
        if i in ["CW", "CCW", "ENTER"]: self.requestBack.emit(); return True
        return False