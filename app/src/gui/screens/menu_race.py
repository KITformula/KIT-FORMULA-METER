from PyQt5.QtCore import QTimer, pyqtSignal, Qt, QSize
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QListWidget, QWidget, QGridLayout, QListWidgetItem
from src.gui.self_defined_widgets import TitleValueBox

# --- Race Menu Screen (Category Top) ---
class RaceMenuScreen(QWidget):
    requestOpenDriver = pyqtSignal()
    requestOpenStartLine = pyqtSignal()
    requestOpenSector = pyqtSignal()
    requestOpenTargetLaps = pyqtSignal()
    requestResetSession = pyqtSignal()
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()

        title = QLabel("RACE SETUP")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #00FF00; margin-bottom: 10px;")
        self.layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { font-size: 40px; background-color: #222; color: white; border: 2px solid #555; }
            QListWidget::item { padding: 20px; }
            QListWidget::item:selected { background-color: #006400; color: white; border: 2px solid #00FF00; }
        """)

        self.items = [
            "1. Driver Select >",
            "2. Set Start Line >",
            "3. Sector Settings >",
            "4. Target Laps >",
            "5. Reset Session Data",
            "6. << BACK"
        ]
        self.list_widget.addItems(self.items)
        self.list_widget.setCurrentRow(0)
        self.layout.addWidget(self.list_widget)
        
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def handle_input(self, input_type: str) -> bool:
        row = self.list_widget.currentRow()
        if input_type == "CW":
            self.list_widget.setCurrentRow(0 if row >= len(self.items)-1 else row + 1)
            return True
        elif input_type == "CCW":
            self.list_widget.setCurrentRow(len(self.items)-1 if row <= 0 else row - 1)
            return True
        elif input_type == "ENTER":
            if row == 0: self.requestOpenDriver.emit()
            elif row == 1: self.requestOpenStartLine.emit()
            elif row == 2: self.requestOpenSector.emit()
            elif row == 3: self.requestOpenTargetLaps.emit()
            elif row == 4: self._perform_reset()
            elif row == 5: self.requestBack.emit()
            return True
        return False

    def _perform_reset(self):
        self.requestResetSession.emit()
        orig_text = self.items[4]
        self.list_widget.item(4).setText("✔ RESET DONE!")
        QTimer.singleShot(1500, lambda: self.list_widget.item(4).setText(orig_text))


# --- Sub Screens ---

class DriverSelectScreen(QWidget):
    driverChanged = pyqtSignal(str)
    requestBack = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("DRIVER SELECT", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: #00FF00;"))
        
        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget { font-size: 40px; background-color: #222; color: white; } 
            QListWidget::item { padding: 20px; }
            QListWidget::item:selected { background-color: #006400; border: 2px solid #00FF00; }
        """)
        
        self.drivers = ["None", "H.BAMOS", "T.Sogai", "D.Toubou", "K.Araki", "K.Isayama", "Y.Tsuneyoshi"]
        
        # 画像アイコンの設定
        flag_icon = QIcon("src/gui/icons/japan.png")
        honda_icon = QIcon("src/gui/icons/Honda.png") # Hondaのロゴを読み込み
        
        self.list.setIconSize(QSize(60, 40)) 

        for name in self.drivers:
            item = QListWidgetItem(name)
            
            # 条件分岐: H.BAMOSならHondaロゴ、それ以外(None除く)は国旗
            if name == "H.BAMOS":
                item.setIcon(honda_icon)
            elif name != "None":
                item.setIcon(flag_icon)
                
            self.list.addItem(item)
        
        self.list.setCurrentRow(0)
        self.layout.addWidget(self.list)
        self.layout.addWidget(QLabel("Push: SELECT & BACK", alignment=Qt.AlignCenter, styleSheet="font-size: 20px; color: #AAA;"))
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def handle_input(self, input_type: str) -> bool:
        row = self.list.currentRow()
        if input_type == "CW": self.list.setCurrentRow(0 if row >= len(self.drivers)-1 else row + 1); return True
        elif input_type == "CCW": self.list.setCurrentRow(len(self.drivers)-1 if row <= 0 else row - 1); return True
        elif input_type == "ENTER":
            # list.currentRow() でインデックスを取得し、self.drivers から名前を取り出す
            self.driverChanged.emit(self.drivers[self.list.currentRow()])
            self.requestBack.emit()
            return True
        return False

class GpsSetScreen(QWidget):
    requestSetLine = pyqtSignal()
    requestBack = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("GPS START LINE", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: cyan;"))
        
        info = QGridLayout()
        self.latBox = TitleValueBox("Latitude"); self.latBox.valueLabel.setFontScale(0.3)
        self.lonBox = TitleValueBox("Longitude"); self.lonBox.valueLabel.setFontScale(0.3)
        self.satsBox = TitleValueBox("Sats/Q"); self.satsBox.valueLabel.setFontScale(0.3)
        info.addWidget(self.latBox, 0, 0); info.addWidget(self.lonBox, 0, 1); info.addWidget(self.satsBox, 1, 0, 1, 2)
        self.layout.addLayout(info)
        
        self.msg = QLabel("SET!", alignment=Qt.AlignCenter, styleSheet="font-size: 40px; color: #0F0; background: rgba(0,0,0,150);"); self.msg.hide()
        self.layout.addWidget(self.msg)
        self.layout.addWidget(QLabel("Push: SET CURRENT POS", alignment=Qt.AlignCenter, styleSheet="font-size: 20px; color: #AAA;"))
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def update_data(self, d):
        self.latBox.updateValueLabel(f"{d.get('latitude',0):.6f}")
        self.lonBox.updateValueLabel(f"{d.get('longitude',0):.6f}")
        self.satsBox.updateValueLabel(f"S:{d.get('sats',0)} Q:{d.get('quality',0)}")

    def handle_input(self, i):
        if self.msg.isVisible(): return True
        if i == "ENTER":
            self.requestSetLine.emit()
            self.msg.show()
            QTimer.singleShot(1500, lambda: [self.msg.hide(), self.requestBack.emit()])
            return True
        elif i in ["CW", "CCW"]: self.requestBack.emit(); return True
        return False

class GpsSectorScreen(QWidget):
    requestSetSector = pyqtSignal(int)
    requestBack = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.current = 1
        self.layout.addWidget(QLabel("SECTOR SETTINGS", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: #F0F;"))
        
        info = QGridLayout()
        self.latBox = TitleValueBox("Lat"); self.lonBox = TitleValueBox("Lon"); self.satsBox = TitleValueBox("Sats")
        for b in [self.latBox, self.lonBox, self.satsBox]: b.valueLabel.setFontScale(0.3)
        info.addWidget(self.latBox, 0, 0); info.addWidget(self.lonBox, 0, 1); info.addWidget(self.satsBox, 1, 0, 1, 2)
        self.layout.addLayout(info)

        self.lbl = QLabel("TARGET: SECTOR 1", alignment=Qt.AlignCenter, styleSheet="font-size: 50px; font-weight: bold; color: yellow;")
        self.layout.addWidget(self.lbl)
        self.msg = QLabel("SET!", alignment=Qt.AlignCenter, styleSheet="font-size: 60px; color: #0F0; background: rgba(0,0,0,200);"); self.msg.hide()
        self.layout.addWidget(self.msg)
        self.layout.addWidget(QLabel("Rotary: Select / Push: SET", alignment=Qt.AlignCenter, styleSheet="font-size: 20px; color: #AAA;"))
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def update_gps_data(self, d):
        self.latBox.updateValueLabel(f"{d.get('latitude',0):.6f}")
        self.lonBox.updateValueLabel(f"{d.get('longitude',0):.6f}")
        self.satsBox.updateValueLabel(f"{d.get('sats',0)}")

    def handle_input(self, i):
        if self.msg.isVisible(): return True # メッセージ表示中は操作ブロック
        
        if i == "CW":
            if self.current < 10: self.current += 1; self.lbl.setText(f"TARGET: SECTOR {self.current}")
            elif self.current == 10: self.current = 11; self.lbl.setText("<< BACK")
            return True
        elif i == "CCW":
            if self.current > 1: self.current -= 1
            if self.current < 11: self.lbl.setText(f"TARGET: SECTOR {self.current}")
            return True
        elif i == "ENTER":
            if self.current == 11: self.requestBack.emit(); return True
            
            # 設定実行
            self.requestSetSector.emit(self.current)
            self.msg.setText(f"SECTOR {self.current}\nSET!")
            self.msg.show()
            
            # ★変更: 1.5秒後に自動で次へ進むメソッドを呼ぶ
            QTimer.singleShot(1500, self._auto_advance)
            return True
        return False

    def _auto_advance(self):
        """設定完了後、自動的に次のセクターを選択状態にする"""
        self.msg.hide()
        
        # 10未満なら次へ進める (例: 1設定後は2へ)
        if self.current < 10:
            self.current += 1
            self.lbl.setText(f"TARGET: SECTOR {self.current}")
        # 10を設定し終わったら BACK(11) へ
        elif self.current == 10:
            self.current = 11
            self.lbl.setText("<< BACK")

class TargetLapsScreen(QWidget):
    requestSetLaps = pyqtSignal(int)
    requestBack = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.laps = 0
        self.layout.addWidget(QLabel("TARGET LAPS", alignment=Qt.AlignCenter, styleSheet="font-size: 32px; font-weight: bold; color: cyan;"))
        self.lbl = QLabel("UNLIMITED", alignment=Qt.AlignCenter, styleSheet="font-size: 80px; font-weight: bold; color: white;")
        self.layout.addWidget(self.lbl)
        self.layout.addWidget(QLabel("Rotary: Set / Push: SET & BACK", alignment=Qt.AlignCenter, styleSheet="font-size: 20px; color: #AAA;"))
        self.setLayout(self.layout)
        p = self.palette(); p.setColor(self.backgroundRole(), QColor("#333")); self.setPalette(p); self.setAutoFillBackground(True)

    def handle_input(self, i):
        if i == "CW": self.laps += 1; self._upd(); return True
        elif i == "CCW": 
            if self.laps > 0: self.laps -= 1; self._upd()
            return True
        elif i == "ENTER": self.requestSetLaps.emit(self.laps); self.requestBack.emit(); return True
        return False
    def _upd(self):
        if self.laps == 0: self.lbl.setText("UNLIMITED"); self.lbl.setStyleSheet("font-size: 60px; font-weight: bold; color: cyan;")
        else: self.lbl.setText(f"{self.laps} LAPS"); self.lbl.setStyleSheet("font-size: 80px; font-weight: bold; color: white;")