# from abc import ABCMeta, abstractmethod
import time
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
    DeltaBox,
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

# ラップタイム整形用のヘルパー関数
def format_lap_time(seconds: float) -> str:
    """秒数を 'M:SS.ms' (分:秒.ミリ秒2桁) 形式の文字列に変換する"""
    if seconds is None or seconds < 0:
        return "0:00.00"
    
    m = int(seconds // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 100)
    
    return f"{m}:{s:02d}.{ms:02d}"


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

        self.setStyleSheet("""
            QGroupBox {
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QGroupBox#LeftBox, QGroupBox#CenterBox, QGroupBox#RightBox {
                background-color: #FFF; 
            }
        """)

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
        
        self.fanSwitchStateTitleValueBox.updateBoolValueLabel(
            dashMachineInfo.fanEnabled
        )
        self.fanSwitchStateTitleValueBox.updateFanWarning(dashMachineInfo.fanEnabled)
        self.brakeBiasTitleValueBox.updateValueLabel(dashMachineInfo.brakePress.bias)
        self.tpsTitleValueBox.updateValueLabel(dashMachineInfo.throttlePosition)
        self.bpsFTitleValueBox.updateValueLabel(dashMachineInfo.brakePress.front)
        self.bpsRTitleValueBox.updateValueLabel(dashMachineInfo.brakePress.rear)
        
        self.batteryIconValueBox.updateBatteryValueLabel(dashMachineInfo.batteryVoltage)
        self.fuelcaluculatorIconValueBox.updateFuelPercentLabel(fuel_percentage)
        
        formatted_time = format_lap_time(dashMachineInfo.currentLapTime)
        self.lapTimeBox.updateValueLabel(formatted_time)
        
        self.lapCountBox.updateValueLabel(dashMachineInfo.lapCount)

        self.deltaBox.updateDelta(dashMachineInfo.lapTimeDiff)

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
        self.rpmLabel.setStyleSheet(
            "border: none; border-radius: 0px; font-weight: bold; color: #FFF; background-color: #000"
        )
        
        self.gearLabel = GearLabel()

        self.waterTempTitleValueBox = TitleValueBox("Water Temp")
        self.oilTempTitleValueBox = TitleValueBox("Oil Temp")
        
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
        
        self.opsBar = PedalBar("#F00", 300)

        self.batteryIconValueBox = IconValueBox()
        self.fuelcaluculatorIconValueBox = IconValueBox()
        self.lapCountLabel = IconValueBox()
        self.tpms_fl = TpmsBox("")
        self.tpms_fr = TpmsBox("")
        self.tpms_rl = TpmsBox("")
        self.tpms_rr = TpmsBox("")

        self.lapTimeBox = TitleValueBox("Lap Time")
        self.lapTimeBox.valueLabel.setFontScale(0.55)

        self.lapCountBox = TitleValueBox("Lap")
        
        self.deltaBox = DeltaBox("Delta")
        
        self.goproLabel = TitleValueBox("GoPro Bat")

    def createTopGroupBox(self):
        self.topGroupBox = QGroupBox()
        self.topGroupBox.setMaximumHeight(60)

        layout = QGridLayout()
        self.rpmLightBar = RpmLightBar()
        layout.addWidget(self.rpmLightBar, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.topGroupBox.setLayout(layout)

    def createLeftGroupBox(self):
        self.leftGroupBox = QGroupBox()
        self.leftGroupBox.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.leftGroupBox.setObjectName("LeftBox") 

        layout = QGridLayout()
        
        layout.addWidget(self.lapTimeBox, 0, 0, 1, 2)
        layout.addWidget(self.waterTempTitleValueBox, 1, 0)
        layout.addWidget(self.oilTempTitleValueBox, 1, 1)
        layout.addWidget(self.batteryIconValueBox, 2, 0, 1, 2)
        layout.addWidget(self.fuelcaluculatorIconValueBox, 3, 0, 1, 2)

        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 1)
        layout.setRowStretch(3, 1)

        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2) 

        self.leftGroupBox.setLayout(layout)

    def createCenterGroupBox(self):
        self.centerGroupBox = QGroupBox()
        self.centerGroupBox.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.centerGroupBox.setObjectName("CenterBox")

        layout = QGridLayout()
        
        layout.addWidget(self.gearLabel, 0, 0, 1, 3, QtCore.Qt.AlignTop) 
        layout.addWidget(self.rpmLabel, 1, 0, 1, 3)
        layout.addWidget(self.tpsTitleValueBox, 2, 0, 1, 3)
        layout.addWidget(self.opsBar, 3, 0, 1, 3)

        layout.setRowStretch(0, 15)
        layout.setRowStretch(1, 3)
        layout.setRowStretch(2, 2)
        layout.setRowStretch(3, 2)

        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.centerGroupBox.setLayout(layout)

    def createRightGroupBox(self):
        self.rightGroupBox = QGroupBox()
        self.rightGroupBox.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.rightGroupBox.setObjectName("RightBox") 

        tpmsGridGroup = QGroupBox()
        tpmsGridGroup.setObjectName("TpmsGridGroup")
        tpmsGridGroup.setStyleSheet("QGroupBox#TpmsGridGroup { background-color: #FFF; border: none; margin: 0px; padding: 0px; }")
        tpmsGridGroup.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        tpmsLayout = QGridLayout()
        tpmsLayout.setContentsMargins(0, 0, 0, 0)
        tpmsLayout.setSpacing(2)

        tpmsLayout.addWidget(self.tpms_fl, 0, 0)
        tpmsLayout.addWidget(self.tpms_fr, 0, 1)
        tpmsLayout.addWidget(self.tpms_rl, 1, 0)
        tpmsLayout.addWidget(self.tpms_rr, 1, 1)

        tpmsGridGroup.setLayout(tpmsLayout)

        mainLayout = QGridLayout()
        mainLayout.setContentsMargins(2, 2, 2, 2)
        mainLayout.setSpacing(2)

        lapInfoContainer = QWidget()
        lapInfoContainer.setObjectName("LapInfoContainer")
        lapInfoContainer.setStyleSheet("QWidget#LapInfoContainer { background-color: #FFF; }") 
        lapInfoContainer.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        
        lapInfoLayout = QGridLayout()
        lapInfoLayout.setContentsMargins(0, 0, 0, 0)
        lapInfoLayout.setSpacing(2)
        
        lapInfoLayout.addWidget(self.deltaBox, 0, 0)
        lapInfoLayout.addWidget(self.lapCountBox, 1, 0)
        
        lapInfoContainer.setLayout(lapInfoLayout)
        
        mainLayout.addWidget(lapInfoContainer, 0, 0)
        mainLayout.addWidget(tpmsGridGroup, 1, 0)
        
        mainLayout.setRowStretch(0, 3)
        mainLayout.setRowStretch(1, 6)

        self.rightGroupBox.setLayout(mainLayout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.requestSetStartLine.emit()
        else:
            super().keyPressEvent(event)


# --- 2. GoPro専用メニュー画面 ---
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
        
        title = QLabel("GoPro Settings")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #00FFFF; margin-bottom: 10px;")
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
                background-color: #008B8B;
                color: white;
                border: 2px solid #00FFFF;
            }
        """)
        
        self.items = [
            "1. Connect / Retry",
            "2. Disconnect",
            "3. Record START",
            "4. Record STOP",
            "5. << BACK"
        ]
        self.list_widget.addItems(self.items)
        self.list_widget.setCurrentRow(0)
        
        self.layout.addWidget(self.list_widget)

        self.status_label = QLabel("Status: Not Connected")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 20px; color: #AAA; border-top: 1px solid #555; padding: 10px;")
        self.layout.addWidget(self.status_label)

        self.battery_label = QLabel("Battery: --%")
        self.battery_label.setAlignment(Qt.AlignCenter)
        self.battery_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #AAA; padding: 10px;")
        self.layout.addWidget(self.battery_label)

        self.setLayout(self.layout)
        
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#333"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def showEvent(self, event):
        self.shown_timestamp = time.time()
        super().showEvent(event)

    def update_status(self, text: str):
        self.status_label.setText(f"Status: {text}")
        
        if "Connected" in text or "Ready" in text or "Recording" in text:
            self.status_label.setStyleSheet("font-size: 20px; color: #0F0; border-top: 1px solid #555; padding: 10px;")
        elif "Error" in text or "Failed" in text:
            self.status_label.setStyleSheet("font-size: 20px; color: #F00; border-top: 1px solid #555; padding: 10px;")
        else:
            self.status_label.setStyleSheet("font-size: 20px; color: #FF0; border-top: 1px solid #555; padding: 10px;")

    def update_battery(self, value: int):
        color = "#0F0" # 緑
        if value < 20:
            color = "#F00" # 赤
        elif value < 50:
            color = "#FF0" # 黄
            
        self.battery_label.setText(f"Battery: {value}%")
        self.battery_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color}; padding: 10px;")

    def handle_input(self, input_type: str) -> bool:
        if time.time() - self.shown_timestamp < 0.5:
            return True

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
                self.update_status("Disconnecting...")
                self.requestDisconnect.emit()
            elif current_row == 2:
                self.requestRecStart.emit()
            elif current_row == 3:
                self.requestRecStop.emit()
            elif current_row == 4:
                self.requestBack.emit()
            return True

        return False


class LSDMenuScreen(QWidget):
    lsdLevelChanged = pyqtSignal(int)
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        
        title = QLabel("LSD ADJUSTMENT")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #FF00FF; margin-bottom: 20px;")
        self.layout.addWidget(title)

        self.current_level = 1
        self.max_level = 5
        self.min_level = 1

        self.level_label = QLabel(f"LEVEL: {self.current_level}")
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setStyleSheet("font-size: 80px; font-weight: bold; color: white;")
        self.layout.addWidget(self.level_label)

        hint_label = QLabel("Rotary: Adjust Level\nPush: BACK")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("font-size: 20px; color: #AAA; margin-top: 20px;")
        self.layout.addWidget(hint_label)

        self.setLayout(self.layout)
        
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#333"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def handle_input(self, input_type: str) -> bool:
        if input_type == "CW":
            if self.current_level < self.max_level:
                self.current_level += 1
                self._update_display()
                self.lsdLevelChanged.emit(self.current_level)
            return True 

        elif input_type == "CCW":
            if self.current_level > self.min_level:
                self.current_level -= 1
                self._update_display()
                self.lsdLevelChanged.emit(self.current_level)
            return True

        elif input_type == "ENTER":
            self.requestBack.emit()
            return True

        return False

    def _update_display(self):
        self.level_label.setText(f"LEVEL: {self.current_level}")


# ★★★ 新規: GPS設定画面 ★★★
class GpsSetScreen(QWidget):
    requestSetLine = pyqtSignal()
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.is_processing = False
        
        title = QLabel("GPS START LINE SETTING")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: cyan; margin-bottom: 20px;")
        self.layout.addWidget(title)

        self.latBox = TitleValueBox("Latitude")
        self.lonBox = TitleValueBox("Longitude")
        self.satsBox = TitleValueBox("Sats/Quality")

        for box in [self.latBox, self.lonBox, self.satsBox]:
            box.valueLabel.setFontScale(0.3)

        infoLayout = QGridLayout()
        infoLayout.addWidget(self.latBox, 0, 0)
        infoLayout.addWidget(self.lonBox, 0, 1)
        infoLayout.addWidget(self.satsBox, 1, 0, 1, 2)
        
        self.layout.addLayout(infoLayout)

        self.message_label = QLabel("START LINE SET!")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("font-size: 40px; font-weight: bold; color: #00FF00; background-color: rgba(0, 0, 0, 150); border-radius: 10px; padding: 10px;")
        self.message_label.hide()
        self.layout.addWidget(self.message_label)

        self.hint_label = QLabel("Push: SET CURRENT POS\nRotary: BACK")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("font-size: 20px; color: #AAA; margin-top: 20px;")
        self.layout.addWidget(self.hint_label)

        self.setLayout(self.layout)
        
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#333"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def showEvent(self, event):
        self.message_label.hide()
        self.hint_label.show()
        self.is_processing = False
        super().showEvent(event)

    def update_data(self, gps_data: dict):
        lat = gps_data.get("latitude", 0.0)
        lon = gps_data.get("longitude", 0.0)
        sats = gps_data.get("sats", 0)
        quality = gps_data.get("quality", 0)

        self.latBox.updateValueLabel(f"{lat:.6f}")
        self.lonBox.updateValueLabel(f"{lon:.6f}")
        self.satsBox.updateValueLabel(f"Sat:{sats} Q:{quality}")

    def handle_input(self, input_type: str) -> bool:
        if self.is_processing:
            return True

        if input_type == "ENTER":
            self.is_processing = True
            self.requestSetLine.emit()
            self.hint_label.hide()
            self.message_label.show()
            QTimer.singleShot(1500, self._finish_and_back)
            return True 
        
        elif input_type in ["CW", "CCW"]:
            self.requestBack.emit()
            return True

        return False

    def _finish_and_back(self):
        self.message_label.hide()
        self.hint_label.show()
        self.is_processing = False
        self.requestBack.emit()

# ★★★ 新規: 燃料リセット画面 ★★★
class FuelResetScreen(QWidget):
    requestReset = pyqtSignal()
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        
        title = QLabel("FUEL INTEGRATOR RESET")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: orange; margin-bottom: 20px;")
        self.layout.addWidget(title)

        self.fuel_label = QLabel("Current: -- %")
        self.fuel_label.setAlignment(Qt.AlignCenter)
        self.fuel_label.setStyleSheet("font-size: 60px; font-weight: bold; color: white;")
        self.layout.addWidget(self.fuel_label)

        self.message_label = QLabel("RESET COMPLETE")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("font-size: 40px; font-weight: bold; color: #00FF00; background-color: rgba(0, 0, 0, 150); border-radius: 10px; padding: 10px;")
        self.message_label.hide()
        self.layout.addWidget(self.message_label)

        self.hint_label = QLabel("Push: RESET 100%\nRotary: BACK")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("font-size: 20px; color: #AAA; margin-top: 20px;")
        self.layout.addWidget(self.hint_label)

        self.setLayout(self.layout)
        
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#333"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def showEvent(self, event):
        self.message_label.hide()
        self.hint_label.show()
        super().showEvent(event)

    def update_fuel(self, percent: float):
        self.fuel_label.setText(f"Current: {int(percent)} %")

    def handle_input(self, input_type: str) -> bool:
        if self.message_label.isVisible(): return True

        if input_type == "ENTER":
            self.requestReset.emit()
            self.hint_label.hide()
            self.message_label.show()
            QTimer.singleShot(1500, self._finish_and_back)
            return True
        elif input_type in ["CW", "CCW"]:
            self.requestBack.emit()
            return True
        return False

    def _finish_and_back(self):
        self.message_label.hide()
        self.hint_label.show()
        self.requestBack.emit()


# ★★★ 新規: 走行距離表示画面 ★★★
class MileageScreen(QWidget):
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        
        title = QLabel("MILEAGE INFO")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #00BFFF; margin-bottom: 20px;")
        self.layout.addWidget(title)

        self.today_label = QLabel("Today: --.- km")
        self.today_label.setAlignment(Qt.AlignCenter)
        self.today_label.setStyleSheet("font-size: 48px; font-weight: bold; color: white;")
        self.layout.addWidget(self.today_label)

        self.total_label = QLabel("Total: ----.- km")
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #AAA;")
        self.layout.addWidget(self.total_label)

        hint_label = QLabel("Rotary: BACK")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("font-size: 20px; color: #AAA; margin-top: 20px;")
        self.layout.addWidget(hint_label)

        self.setLayout(self.layout)
        
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#333"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def update_distance(self, daily_km: float, total_km: float):
        self.today_label.setText(f"Today: {daily_km:.1f} km")
        self.total_label.setText(f"Total: {total_km:.1f} km")

    def handle_input(self, input_type: str) -> bool:
        if input_type in ["CW", "CCW", "ENTER"]:
            self.requestBack.emit()
            return True
        return False


# ★★★ 新規: GPS Sector 設定画面（プレースホルダー） ★★★
class GpsSectorScreen(QWidget):
    requestSetSector = pyqtSignal(int)  # ★追加: セクター設定シグナル
    requestBack = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.current_sector = 1 # 現在選択中のセクター
        self.is_processing = False
        
        title = QLabel("GPS SECTOR SETTINGS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #FF00FF; margin-bottom: 10px;")
        self.layout.addWidget(title)

        # GPS情報表示部 (上段)
        infoLayout = QGridLayout()
        self.latBox = TitleValueBox("Latitude")
        self.lonBox = TitleValueBox("Longitude")
        self.satsBox = TitleValueBox("Sats/Quality")
        
        for box in [self.latBox, self.lonBox, self.satsBox]:
            box.valueLabel.setFontScale(0.3)
            
        infoLayout.addWidget(self.latBox, 0, 0)
        infoLayout.addWidget(self.lonBox, 0, 1)
        infoLayout.addWidget(self.satsBox, 1, 0, 1, 2)
        self.layout.addLayout(infoLayout)

        # セクター選択部 (中段)
        self.sectorLabel = QLabel("TARGET: SECTOR 1")
        self.sectorLabel.setAlignment(Qt.AlignCenter)
        self.sectorLabel.setStyleSheet("font-size: 50px; font-weight: bold; color: yellow; margin: 20px;")
        self.layout.addWidget(self.sectorLabel)

        # 設定完了メッセージ (オーバーレイ的扱い)
        self.message_label = QLabel("SET!")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("font-size: 60px; font-weight: bold; color: #00FF00; background-color: rgba(0, 0, 0, 200); border-radius: 10px;")
        self.message_label.hide()
        self.layout.addWidget(self.message_label)

        # 操作説明 (下段)
        self.hint_label = QLabel("Rotary: Select Sector\nPush: SET POS\n") # ★修正: BACKの操作を追加したいが…
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("font-size: 20px; color: #AAA; margin-top: 10px;")
        self.layout.addWidget(self.hint_label)

        self.setLayout(self.layout)
        
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#333"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def showEvent(self, event):
        self.message_label.hide()
        self.hint_label.show()
        self.is_processing = False
        super().showEvent(event)

    def update_gps_data(self, gps_data: dict):
        lat = gps_data.get("latitude", 0.0)
        lon = gps_data.get("longitude", 0.0)
        sats = gps_data.get("sats", 0)
        quality = gps_data.get("quality", 0)

        self.latBox.updateValueLabel(f"{lat:.6f}")
        self.lonBox.updateValueLabel(f"{lon:.6f}")
        self.satsBox.updateValueLabel(f"Sat:{sats} Q:{quality}")

    def handle_input(self, input_type: str) -> bool:
        if self.is_processing:
            return True

        if input_type == "CW":
            if self.current_sector < 10: # 最大10セクターまで
                self.current_sector += 1
                self.sectorLabel.setText(f"TARGET: SECTOR {self.current_sector}")
            elif self.current_sector == 10: # 10の次はBACK
                self.current_sector = 11 # 11 = BACK
                self.sectorLabel.setText("<< BACK")
            return True

        elif input_type == "CCW":
            if self.current_sector > 1:
                self.current_sector -= 1
                if self.current_sector < 11:
                    self.sectorLabel.setText(f"TARGET: SECTOR {self.current_sector}")
            return True

        elif input_type == "ENTER":
            # BACKが選択されている場合
            if self.current_sector == 11:
                self.requestBack.emit()
                return True

            # セクター設定処理
            self.is_processing = True
            self.requestSetSector.emit(self.current_sector)
            
            self.hint_label.hide()
            self.message_label.setText(f"SECTOR {self.current_sector}\nSET!")
            self.message_label.show()
            
            QTimer.singleShot(1500, self._finish_processing)
            return True
            
        return False

    def _finish_processing(self):
        self.message_label.hide()
        self.hint_label.show()
        self.is_processing = False


# --- 3. 設定画面 ---
class SettingsScreen(QWidget):
    requestOpenGpsMenu = pyqtSignal()
    requestOpenFuelMenu = pyqtSignal()
    requestOpenGoProMenu = pyqtSignal()
    requestOpenLSDMenu = pyqtSignal()
    requestLapTimeSetup = pyqtSignal()
    requestOpenMileageMenu = pyqtSignal()
    requestOpenGpsSectorMenu = pyqtSignal() # ★新規: GPS Sectorメニュー用シグナル
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
            "1. Set GPS Start Line >",
            "2. Fuel Reset Menu >", 
            "3. GoPro Menu >",
            "4. LSD Adjustment >",
            "5. Lap Time Settings",
            "6. GPS Sector Settings >", # ★新規: 項目追加
            "7. Mileage Info >",
            "8. EXIT"
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
                self.requestOpenGpsMenu.emit()
            elif current_row == 1:
                self.requestOpenFuelMenu.emit() 
            elif current_row == 2:
                self.requestOpenGoProMenu.emit()
            elif current_row == 3:
                self.requestOpenLSDMenu.emit()
            elif current_row == 4:
                self.requestLapTimeSetup.emit()
            elif current_row == 5:
                self.requestOpenGpsSectorMenu.emit() # ★新規
            elif current_row == 6:
                self.requestOpenMileageMenu.emit()
            elif current_row == 7:
                self.requestExit.emit()
            return True

        return False


# --- 4. メインウィンドウ ---
class MainDisplayWindow(QDialog):
    requestSetStartLine = pyqtSignal()
    requestResetFuel = pyqtSignal()
    requestGoProConnect = pyqtSignal()
    requestGoProDisconnect = pyqtSignal()
    requestGoProRecStart = pyqtSignal()
    requestGoProRecStop = pyqtSignal()
    requestLapTimeSetup = pyqtSignal()
    requestLsdChange = pyqtSignal(int)
    requestSetSector = pyqtSignal(int) # ★新規: セクター設定用シグナル

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
        self.settings.requestOpenGpsMenu.connect(self.open_gps_menu)
        self.settings.requestOpenFuelMenu.connect(self.open_fuel_menu)
        self.settings.requestOpenGoProMenu.connect(self.open_gopro_menu)
        self.settings.requestOpenLSDMenu.connect(self.open_lsd_menu)
        self.settings.requestLapTimeSetup.connect(self.requestLapTimeSetup.emit)
        self.settings.requestOpenMileageMenu.connect(self.open_mileage_menu)
        self.settings.requestOpenGpsSectorMenu.connect(self.open_gps_sector_menu) # ★新規
        self.settings.requestExit.connect(self.return_to_dashboard)
        
        # 3. GoPro Menu
        self.gopro_menu = GoProMenuScreen()
        self.gopro_menu.requestConnect.connect(self.requestGoProConnect.emit)
        self.gopro_menu.requestDisconnect.connect(self.requestGoProDisconnect.emit)
        self.gopro_menu.requestRecStart.connect(self.requestGoProRecStart.emit)
        self.gopro_menu.requestRecStop.connect(self.requestGoProRecStop.emit)
        self.gopro_menu.requestBack.connect(self.return_to_settings)

        # 4. LSD Menu
        self.lsd_menu = LSDMenuScreen()
        self.lsd_menu.lsdLevelChanged.connect(self.requestLsdChange.emit)
        self.lsd_menu.requestBack.connect(self.return_to_settings)

        # 5. GPS Set Screen
        self.gps_screen = GpsSetScreen()
        self.gps_screen.requestSetLine.connect(self.requestSetStartLine.emit)
        self.gps_screen.requestBack.connect(self.return_to_settings)
        
        # 6. Fuel Reset Screen
        self.fuel_screen = FuelResetScreen()
        self.fuel_screen.requestReset.connect(self.requestResetFuel.emit)
        self.fuel_screen.requestBack.connect(self.return_to_settings)

        # 7. Mileage Screen
        self.mileage_screen = MileageScreen()
        self.mileage_screen.requestBack.connect(self.return_to_settings)

        # 8. GPS Sector Screen (★新規)
        self.gps_sector_screen = GpsSectorScreen()
        self.gps_sector_screen.requestBack.connect(self.return_to_settings)
        self.gps_sector_screen.requestSetSector.connect(self.requestSetSector.emit) # シグナル転送

        self.stack.addWidget(self.dashboard)   # Index 0
        self.stack.addWidget(self.settings)    # Index 1
        self.stack.addWidget(self.gopro_menu)  # Index 2
        self.stack.addWidget(self.lsd_menu)    # Index 3
        self.stack.addWidget(self.gps_screen)  # Index 4
        self.stack.addWidget(self.fuel_screen) # Index 5
        self.stack.addWidget(self.mileage_screen) # Index 6
        self.stack.addWidget(self.gps_sector_screen) # Index 7
        
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def return_to_dashboard(self):
        self.stack.setCurrentWidget(self.dashboard)

    def open_gopro_menu(self):
        self.stack.setCurrentWidget(self.gopro_menu)

    def open_lsd_menu(self):
        self.stack.setCurrentWidget(self.lsd_menu)

    def open_gps_menu(self):
        self.stack.setCurrentWidget(self.gps_screen)
    
    def open_fuel_menu(self):
        self.stack.setCurrentWidget(self.fuel_screen)

    def open_mileage_menu(self):
        self.stack.setCurrentWidget(self.mileage_screen)

    def open_gps_sector_menu(self): # ★新規
        self.stack.setCurrentWidget(self.gps_sector_screen)

    def return_to_settings(self):
        self.stack.setCurrentWidget(self.settings)

    def updateGoProStatus(self, text: str):
        self.gopro_menu.update_status(text)

    def updateGoProBattery(self, value: int):
        self.dashboard.updateGoProBattery(value)
        self.gopro_menu.update_battery(value)

    def updateDashboard(self, dashMachineInfo, fuel_percentage, tpms_data, gps_data, daily_km=0.0, total_km=0.0): 
        current_widget = self.stack.currentWidget()

        if current_widget == self.dashboard:
            self.dashboard.updateDashboard(dashMachineInfo, fuel_percentage, tpms_data)
        
        elif current_widget == self.gps_screen:
            self.gps_screen.update_data(gps_data)

        elif current_widget == self.fuel_screen:
            self.fuel_screen.update_fuel(fuel_percentage)

        elif current_widget == self.mileage_screen:
            self.mileage_screen.update_distance(daily_km, total_km)
            
        elif current_widget == self.gps_sector_screen:
            self.gps_sector_screen.update_gps_data(gps_data)

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
            self.stack.setCurrentWidget(self.settings)