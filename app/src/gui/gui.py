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


# --- 1. ダッシュボード画面 (変更なし) ---
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

        mainLayout.setRowStretch(0, 1)
        mainLayout.setRowStretch(1, 2)
        mainLayout.setRowStretch(2, 7)

        self.rightGroupBox.setLayout(mainLayout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.requestSetStartLine.emit()
        else:
            super().keyPressEvent(event)


# --- 2. 設定画面 (修正版) ---
class SettingsScreen(QWidget):
    requestSetStartLine = pyqtSignal()
    requestResetFuel = pyqtSignal()
    requestGoproSetup = pyqtSignal()
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
            "3. GoPro Connect / Settings", # 文言変更
            "4. Lap Time Settings",
            "5. EXIT"
        ]
        self.list_widget.addItems(self.items)
        self.list_widget.setCurrentRow(0)
        
        self.layout.addWidget(self.list_widget)

        # ★ GoProステータス表示エリア
        self.gopro_status_label = QLabel("GoPro Status: Not Connected")
        self.gopro_status_label.setAlignment(Qt.AlignCenter)
        self.gopro_status_label.setStyleSheet("font-size: 20px; color: #AAA; border-top: 1px solid #555; padding: 10px;")
        self.layout.addWidget(self.gopro_status_label)

        self.setLayout(self.layout)
        
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#333"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def update_gopro_status(self, text: str):
        """GoProのステータス表示を更新するメソッド"""
        self.gopro_status_label.setText(f"GoPro Status: {text}")
        
        # ★★★ 修正ポイント: "Connected" や "Ready" が含まれていれば緑色にする ★★★
        if "Connected" in text or "Ready" in text or "Recording" in text:
            # 接続完了 or 録画中は緑色背景
            self.gopro_status_label.setStyleSheet("font-size: 20px; color: #0F0; border-top: 1px solid #555; padding: 10px;")
        elif "Error" in text or "Failed" in text:
            # エラー時は赤文字
            self.gopro_status_label.setStyleSheet("font-size: 20px; color: #F00; border-top: 1px solid #555; padding: 10px;")
        else:
            # その他（待機中など）は黄色
            self.gopro_status_label.setStyleSheet("font-size: 20px; color: #FF0; border-top: 1px solid #555; padding: 10px;")

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
            elif current_row == 2: # GoPro
                self.requestGoproSetup.emit()
            elif current_row == 3:
                self.requestLapTimeSetup.emit()
            elif current_row == 4:
                self.requestExit.emit()
            return True

        return False

# --- 3. メインウィンドウ ---
class MainDisplayWindow(QDialog):
    requestSetStartLine = pyqtSignal()
    requestResetFuel = pyqtSignal()
    requestGoproSetup = pyqtSignal()
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
        
        # ... (DashboardWidgetはそのまま) ...
        self.dashboard = DashboardWidget(listener)
        self.dashboard.requestSetStartLine.connect(self.requestSetStartLine.emit)
        
        # ... (SettingsScreenのインスタンス化) ...
        self.settings = SettingsScreen()
        
        self.settings.requestSetStartLine.connect(self.requestSetStartLine.emit)
        self.settings.requestResetFuel.connect(self.requestResetFuel.emit)
        self.settings.requestGoproSetup.connect(self.requestGoproSetup.emit)
        self.settings.requestLapTimeSetup.connect(self.requestLapTimeSetup.emit)
        self.settings.requestExit.connect(self.return_to_dashboard)
        
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.settings)
        
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    # ★★★ 追加: GoProステータス更新用メソッド ★★★
    def updateGoProStatus(self, text: str):
        """Applicationから呼ばれて、SettingsScreenの表示を更新する"""
        self.settings.update_gopro_status(text)

    # ... (updateDashboard, input_cwなどは前回と同じ) ...
    def updateDashboard(self, dashMachineInfo, fuel_percentage, tpms_data):
        if self.stack.currentWidget() == self.dashboard:
            self.dashboard.updateDashboard(dashMachineInfo, fuel_percentage, tpms_data)

    def return_to_dashboard(self):
        self.stack.setCurrentWidget(self.dashboard)

    def input_cw(self):
        self._dispatch_input("CW", direction=1)

    def input_ccw(self):
        self._dispatch_input("CCW", direction=-1)

    def input_enter(self):
        self._dispatch_input("ENTER")

    def _dispatch_input(self, input_type, direction=0):
        current_widget = self.stack.currentWidget()
        
        if hasattr(current_widget, "handle_input"):
            consumed = current_widget.handle_input(input_type)
            if consumed:
                return

        if input_type in ["CW", "CCW"] and current_widget == self.dashboard:
            self.switch_screen(direction)

    def switch_screen(self, direction):
        current = self.stack.currentIndex()
        count = self.stack.count()
        next_index = (current + direction) % count
        self.stack.setCurrentIndex(next_index)