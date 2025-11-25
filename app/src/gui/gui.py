# from abc import ABCMeta, abstractmethod

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QGroupBox,
    QWidget,
    QStackedWidget,
    QLabel,
    QVBoxLayout,
    QListWidget,
)

from src.gui.self_defined_widgets import (
    GearLabel,
    IconValueBox,
    PedalBar,
    RpmLabel,
    RpmLightBar,
    TitleValueBox,
    TpmsBox,
)
from src.models.models import (
    DashMachineInfo,
)


class WindowListener:
    def onUpdate(self) -> None:
        pass


# --- 1. ダッシュボード画面 ---
class DashboardWidget(QWidget):
    requestSetStartLine = pyqtSignal()

    def __init__(self, listener: WindowListener):
        super(DashboardWidget, self).__init__(None)
        self.listener = listener
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.listener.onUpdate)
        self.timer.start(50)

        palette = QApplication.palette()
        palette.setColor(self.backgroundRole(), QColor("#000"))
        palette.setColor(self.foregroundRole(), QColor("#FFF"))
        self.setPalette(palette)

        self.createAllWidgets()
        self.createTopGroupBox()
        self.createLeftGroupBox()
        self.createCenterGroupBox()
        self.createRightGroupBox()

        mainLayout = QGridLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        self.setLayout(mainLayout)
        mainLayout.addWidget(self.topGroupBox, 0, 0, 1, 3)
        mainLayout.addWidget(self.leftGroupBox, 1, 0, 1, 1)
        mainLayout.addWidget(self.centerGroupBox, 1, 1, 1, 1)
        mainLayout.addWidget(self.rightGroupBox, 1, 2, 1, 1)

        mainLayout.setColumnStretch(0, 3)
        mainLayout.setColumnStretch(1, 2)
        mainLayout.setColumnStretch(2, 3)
        mainLayout.setRowStretch(0, 1)
        mainLayout.setRowStretch(1, 1)
        mainLayout.setRowStretch(2, 0)

    def updateGoProBattery(self, value: int):
        color = "#0F0" # 緑
        if value < 20:
            color = "#F00" # 赤
        elif value < 50:
            color = "#FF0" # 黄
            
        self.goproLabel.updateValueLabel(f"{value}%")
        self.goproLabel.valueLabel.setStyleSheet(f"color: {color}; font-size: 30px; font-weight: bold;")

    def handle_input(self, input_type: str) -> bool:
        return False

    def updateDashboard(
        self, dashMachineInfo: DashMachineInfo, fuel_percentage: float, tpms_data: dict
    ):
        self.rpmLightBar.updateRpmBar(dashMachineInfo.rpm)
        self.rpmLabel.updateRpmLabel(dashMachineInfo.rpm)
        self.gearLabel.updateGearLabel(dashMachineInfo.gearVoltage.gearType)
        self.waterTempTitleValueBox.updateTempValueLabel(dashMachineInfo.waterTemp)
        self.waterTempTitleValueBox.updateWaterTempWarning(dashMachineInfo.waterTemp)
        self.oilTempTitleValueBox.updateTempValueLabel(dashMachineInfo.oilTemp)
        self.oilTempTitleValueBox.updateOilTempWarning(dashMachineInfo.oilTemp)
        self.opsBar.updatePedalBar(dashMachineInfo.oilPress.oilPress)
        self.fuelPressIconValueBox.updateFuelPressValueLabel(dashMachineInfo.fuelPress)
        self.fanSwitchStateTitleValueBox.updateBoolValueLabel(
            dashMachineInfo.fanEnabled
        )
        self.fanSwitchStateTitleValueBox.updateFanWarning(dashMachineInfo.fanEnabled)
        self.brakeBiasTitleValueBox.updateValueLabel(dashMachineInfo.brakePress.bias)
        self.tpsTitleValueBox.updateValueLabel(dashMachineInfo.throttlePosition)
        self.bpsFTitleValueBox.updateValueLabel(dashMachineInfo.brakePress.front)
        self.bpsRTitleValueBox.updateValueLabel(dashMachineInfo.brakePress.rear)
        self.tpsBar.updatePedalBar(dashMachineInfo.throttlePosition)
        self.batteryIconValueBox.updateBatteryValueLabel(dashMachineInfo.batteryVoltage)
        self.fuelcaluculatorIconValueBox.updateFuelPercentLabel(fuel_percentage)
        self.lapTimeBox.updateValueLabel(f"{dashMachineInfo.currentLapTime:.2f}")
        self.lapCountBox.updateValueLabel(dashMachineInfo.lapCount)

        diff = dashMachineInfo.lapTimeDiff
        sign = "+" if diff > 0 else ""
        self.deltaBox.updateValueLabel(f"{sign}{diff:.2f}")

        fl_data = tpms_data.get("FL", {})
        self.tpms_fl.updateTemperature(fl_data.get("temp_c"))
        self.tpms_fl.updatePressure(fl_data.get("pressure_kpa"))

        fr_data = tpms_data.get("FR", {})
        self.tpms_fr.updateTemperature(fr_data.get("temp_c"))
        self.tpms_fr.updatePressure(fr_data.get("pressure_kpa"))

        rl_data = tpms_data.get("RL", {})
        self.tpms_rl.updateTemperature(rl_data.get("temp_c"))
        self.tpms_rl.updatePressure(rl_data.get("pressure_kpa"))

        rr_data = tpms_data.get("RR", {})
        self.tpms_rr.updateTemperature(rr_data.get("temp_c"))
        self.tpms_rr.updatePressure(rr_data.get("pressure_kpa"))

    def createAllWidgets(self):
        self.rpmLabel = RpmLabel()
        self.gearLabel = GearLabel()

        self.waterTempTitleValueBox = TitleValueBox("Water Temp")
        self.oilTempTitleValueBox = TitleValueBox("Oil Temp")
        self.fuelPressIconValueBox = IconValueBox()
        self.fanSwitchStateTitleValueBox = TitleValueBox("Fan Switch")
        self.switchStateRemiderLabel = TitleValueBox(
            "SWITCH CHECK! \n1. Fan \n2. TPS MAX"
        )
        self.switchStateRemiderLabel.titleLabel.setAlignment(QtCore.Qt.AlignVCenter)
        self.switchStateRemiderLabel.titleLabel.setFontScale(0.25)
        self.switchStateRemiderLabel.layout.setRowStretch(0, 1)
        self.switchStateRemiderLabel.layout.setRowStretch(1, 0)

        self.tpsTitleValueBox = TitleValueBox("TPS")
        self.bpsFTitleValueBox = TitleValueBox("BPS F")
        self.bpsRTitleValueBox = TitleValueBox("BPS R")
        self.brakeBiasTitleValueBox = TitleValueBox("Brake\nBias F%")
        self.tpsBar = PedalBar("#0F0", 100)
        self.opsBar = PedalBar("#F00", 300)

        self.batteryIconValueBox = IconValueBox()
        self.fuelcaluculatorIconValueBox = IconValueBox()
        self.lapCountLabel = IconValueBox()
        self.tpms_fl = TpmsBox("FL")
        self.tpms_fr = TpmsBox("FR")
        self.tpms_rl = TpmsBox("RL")
        self.tpms_rr = TpmsBox("RR")

        self.lapTimeBox = TitleValueBox("Lap Time")
        self.lapCountBox = TitleValueBox("Lap")
        self.deltaBox = TitleValueBox("Delta")
        
        self.goproLabel = TitleValueBox("GoPro Bat")

    def createTopGroupBox(self):
        self.topGroupBox = QGroupBox()
        self.topGroupBox.setFlat(True)
        self.topGroupBox.setMaximumHeight(60)

        layout = QGridLayout()
        self.rpmLightBar = RpmLightBar()
        layout.addWidget(self.rpmLightBar, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.topGroupBox.setLayout(layout)

    def createLeftGroupBox(self):
        self.leftGroupBox = QGroupBox()
        self.leftGroupBox.setFlat(True)
        self.leftGroupBox.setObjectName("LeftBox")
        self.leftGroupBox.setStyleSheet("QGroupBox#LeftBox { border: 2px solid white;}")

        layout = QGridLayout()

        layout.addWidget(self.waterTempTitleValueBox, 0, 1)
        layout.addWidget(self.oilTempTitleValueBox, 1, 1)
        layout.addWidget(self.batteryIconValueBox, 2, 1)
        layout.addWidget(self.fuelPressIconValueBox, 3, 1)
        layout.addWidget(self.fuelcaluculatorIconValueBox, 4, 1)

        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 1)
        layout.setRowStretch(3, 1)
        layout.setRowStretch(4, 1)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.leftGroupBox.setLayout(layout)

    def createCenterGroupBox(self):
        self.centerGroupBox = QGroupBox()
        self.centerGroupBox.setFlat(True)
        self.centerGroupBox.setStyleSheet("border: 2px solid white;")

        layout = QGridLayout()

        layout.addWidget(self.rpmLabel, 0, 0, 1, 3)
        layout.addWidget(self.gearLabel, 1, 0, 1, 3)
        layout.addWidget(self.lapTimeBox, 2, 0, 1, 3)
        layout.addWidget(self.tpsBar, 3, 1, 1, 2)
        layout.addWidget(self.tpsTitleValueBox, 3, 0, 1, 1)

        layout.setRowStretch(0, 2)
        layout.setRowStretch(1, 10)
        layout.setRowStretch(2, 4)
        layout.setRowStretch(3, 2)

        self.centerGroupBox.setLayout(layout)

    def createRightGroupBox(self):
        self.rightGroupBox = QGroupBox()
        self.rightGroupBox.setFlat(True)
        self.rightGroupBox.setObjectName("RightBox")
        self.rightGroupBox.setStyleSheet(
            "QGroupBox#RightBox { border: 2px solid white;}"
        )

        tpmsGridGroup = QGroupBox("TPMS")
        tpmsGridGroup.setFlat(True)
        tpmsGridGroup.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFF;")

        tpmsLayout = QGridLayout()
        tpmsLayout.setContentsMargins(0, 0, 0, 0)
        tpmsLayout.setSpacing(5)

        tpmsLayout.addWidget(self.tpms_fl, 0, 0)
        tpmsLayout.addWidget(self.tpms_fr, 0, 1)
        tpmsLayout.addWidget(self.tpms_rl, 1, 0)
        tpmsLayout.addWidget(self.tpms_rr, 1, 1)

        tpmsGridGroup.setLayout(tpmsLayout)

        mainLayout = QGridLayout()
        mainLayout.setContentsMargins(5, 5, 5, 5)
        mainLayout.setSpacing(5)

        mainLayout.addWidget(self.opsBar, 0, 0)

        lapInfoLayout = QGridLayout()
        lapInfoLayout.addWidget(self.lapCountBox, 0, 0)
        lapInfoLayout.addWidget(self.deltaBox, 0, 1)

        mainLayout.addLayout(lapInfoLayout, 1, 0)
        mainLayout.addWidget(tpmsGridGroup, 2, 0)
        
        mainLayout.addWidget(self.goproLabel, 3, 0)

        mainLayout.setRowStretch(0, 1)
        mainLayout.setRowStretch(1, 2)
        mainLayout.setRowStretch(2, 6)
        mainLayout.setRowStretch(3, 2)

        self.rightGroupBox.setLayout(mainLayout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.requestSetStartLine.emit()
        else:
            super().keyPressEvent(event)


# --- 2. GoPro専用メニュー画面 (修正済) ---
class GoProMenuScreen(QWidget):
    # 操作シグナル
    requestConnect = pyqtSignal()
    requestRecStart = pyqtSignal()
    requestRecStop = pyqtSignal()
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        
        # タイトル
        title = QLabel("GoPro Settings")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #00FFFF; margin-bottom: 10px;")
        self.layout.addWidget(title)

        # メニューリスト
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                font-size: 24px;
                background-color: #222;
                color: white;
                border: 2px solid #555;
            }
            QListWidget::item {
                padding: 15px;
            }
            QListWidget::item:selected {
                background-color: #008B8B;
                color: white;
                border: 2px solid #00FFFF;
            }
        """)
        
        self.items = [
            "1. Connect / Retry",
            "2. Record START",
            "3. Record STOP",
            "4. << BACK"
        ]
        self.list_widget.addItems(self.items)
        self.list_widget.setCurrentRow(0)
        
        self.layout.addWidget(self.list_widget)

        # ステータス表示エリア
        self.status_label = QLabel("Status: Not Connected")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 20px; color: #AAA; border-top: 1px solid #555; padding: 10px;")
        self.layout.addWidget(self.status_label)

        # ★★★ 追加: バッテリー表示エリア（一番下） ★★★
        self.battery_label = QLabel("Battery: --%")
        self.battery_label.setAlignment(Qt.AlignCenter)
        self.battery_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #AAA; padding: 10px;")
        self.layout.addWidget(self.battery_label)

        self.setLayout(self.layout)
        
        # 背景色
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#333"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def update_status(self, text: str):
        """Workerからのステータス通知を表示"""
        self.status_label.setText(f"Status: {text}")
        
        if "Connected" in text or "Ready" in text or "Recording" in text:
            self.status_label.setStyleSheet("font-size: 20px; color: #0F0; border-top: 1px solid #555; padding: 10px;")
        elif "Error" in text or "Failed" in text:
            self.status_label.setStyleSheet("font-size: 20px; color: #F00; border-top: 1px solid #555; padding: 10px;")
        else:
            self.status_label.setStyleSheet("font-size: 20px; color: #FF0; border-top: 1px solid #555; padding: 10px;")

    def update_battery(self, value: int):
        """Workerからのバッテリー通知を表示"""
        color = "#0F0" # 緑
        if value < 20:
            color = "#F00" # 赤
        elif value < 50:
            color = "#FF0" # 黄
            
        self.battery_label.setText(f"Battery: {value}%")
        self.battery_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color}; padding: 10px;")

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
                self.requestConnect.emit()
            elif current_row == 1:
                self.requestRecStart.emit()
            elif current_row == 2:
                self.requestRecStop.emit()
            elif current_row == 3:
                self.requestBack.emit()
            return True

        return False


# --- 3. 設定画面 ---
class SettingsScreen(QWidget):
    requestSetStartLine = pyqtSignal()
    requestResetFuel = pyqtSignal()
    requestOpenGoProMenu = pyqtSignal()
    requestLapTimeSetup = pyqtSignal()
    requestExit = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        
        title = QLabel("SETTINGS MENU")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: yellow; margin-bottom: 10px;")
        self.layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                font-size: 24px;
                background-color: #222;
                color: white;
                border: 2px solid #555;
            }
            QListWidget::item {
                padding: 15px;
            }
            QListWidget::item:selected {
                background-color: #00A;
                color: white;
                border: 2px solid yellow;
            }
        """)
        
        self.items = [
            "1. Set GPS Start Line",
            "2. Reset Fuel Integrator",
            "3. GoPro Menu >",
            "4. Lap Time Settings",
            "5. EXIT"
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
                self.requestSetStartLine.emit()
            elif current_row == 1:
                self.requestResetFuel.emit()
            elif current_row == 2:
                self.requestOpenGoProMenu.emit()
            elif current_row == 3:
                self.requestLapTimeSetup.emit()
            elif current_row == 4:
                self.requestExit.emit()
            return True

        return False


# --- 4. メインウィンドウ ---
class MainDisplayWindow(QDialog):
    requestSetStartLine = pyqtSignal()
    requestResetFuel = pyqtSignal()
    requestGoProConnect = pyqtSignal()
    requestGoProRecStart = pyqtSignal()
    requestGoProRecStop = pyqtSignal()
    requestLapTimeSetup = pyqtSignal()

    def __init__(self, listener: WindowListener):
        super(MainDisplayWindow, self).__init__(None)
        self.resize(800, 480)
        
        palette = QApplication.palette()
        palette.setColor(self.backgroundRole(), QColor("#000"))
        palette.setColor(self.foregroundRole(), QColor("#FFF"))
        self.setPalette(palette)

        self.listener = listener
        self.stack = QStackedWidget()
        
        # 1. Dashboard
        self.dashboard = DashboardWidget(listener)
        self.dashboard.requestSetStartLine.connect(self.requestSetStartLine.emit)
        
        # 2. Settings (Main Menu)
        self.settings = SettingsScreen()
        self.settings.requestSetStartLine.connect(self.requestSetStartLine.emit)
        self.settings.requestResetFuel.connect(self.requestResetFuel.emit)
        self.settings.requestOpenGoProMenu.connect(self.open_gopro_menu)
        self.settings.requestLapTimeSetup.connect(self.requestLapTimeSetup.emit)
        self.settings.requestExit.connect(self.return_to_dashboard)
        
        # 3. GoPro Menu (Sub Menu)
        self.gopro_menu = GoProMenuScreen()
        self.gopro_menu.requestConnect.connect(self.requestGoProConnect.emit)
        self.gopro_menu.requestRecStart.connect(self.requestGoProRecStart.emit)
        self.gopro_menu.requestRecStop.connect(self.requestGoProRecStop.emit)
        self.gopro_menu.requestBack.connect(self.return_to_settings)
        
        self.stack.addWidget(self.dashboard)   # Index 0
        self.stack.addWidget(self.settings)    # Index 1
        self.stack.addWidget(self.gopro_menu)  # Index 2
        
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    # --- 画面遷移系メソッド ---
    def return_to_dashboard(self):
        self.stack.setCurrentWidget(self.dashboard)

    def open_gopro_menu(self):
        self.stack.setCurrentWidget(self.gopro_menu)

    def return_to_settings(self):
        self.stack.setCurrentWidget(self.settings)

    # --- ステータス更新用 ---
    def updateGoProStatus(self, text: str):
        """Applicationから呼ばれて、GoProメニューの表示を更新"""
        self.gopro_menu.update_status(text)

    def updateGoProBattery(self, value: int):
        """Applicationから呼ばれて、ダッシュボードとメニュー両方のバッテリー表示を更新"""
        self.dashboard.updateGoProBattery(value)
        # ★★★ 追加: GoProメニュー画面のバッテリー表示も更新 ★★★
        self.gopro_menu.update_battery(value)

    # --- 描画更新 ---
    def updateDashboard(self, dashMachineInfo, fuel_percentage, tpms_data):
        if self.stack.currentWidget() == self.dashboard:
            self.dashboard.updateDashboard(dashMachineInfo, fuel_percentage, tpms_data)

    # --- 入力処理 ---
    def input_cw(self):
        self._dispatch_input("CW", direction=1)

    def input_ccw(self):
        self._dispatch_input("CCW", direction=-1)

    def input_enter(self):
        self._dispatch_input("ENTER")

    def _dispatch_input(self, input_type, direction=0):
        current_widget = self.stack.currentWidget()
        
        # 現在の画面に入力を委譲
        if hasattr(current_widget, "handle_input"):
            consumed = current_widget.handle_input(input_type)
            if consumed:
                return

        # ダッシュボード画面のみ、ロータリーで設定画面へ遷移できる（トグル動作）
        if input_type in ["CW", "CCW"] and current_widget == self.dashboard:
            self.stack.setCurrentWidget(self.settings)