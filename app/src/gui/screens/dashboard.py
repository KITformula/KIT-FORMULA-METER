import time
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGridLayout, QGroupBox, QWidget, QApplication

from src.gui.self_defined_widgets import (
    DeltaBox, GearLabel, IconValueBox, PedalBar,
    RpmLabel, RpmLightBar, TitleValueBox, TpmsBox,
)
from src.models.models import DashMachineInfo

def format_lap_time(seconds: float) -> str:
    if seconds is None or seconds < 0: return "0:00.00"
    m = int(seconds // 60); s = int(seconds % 60); ms = int((seconds - int(seconds)) * 100)
    return f"{m}:{s:02d}.{ms:02d}"

class WindowListener:
    def onUpdate(self) -> None: pass

class DashboardWidget(QWidget):
    requestSetStartLine = pyqtSignal()

    def __init__(self, listener: WindowListener):
        super(DashboardWidget, self).__init__(None)
        self.listener = listener
        self.timer = QTimer(self); self.timer.timeout.connect(self.listener.onUpdate); self.timer.start(50)
        p = QApplication.palette(); p.setColor(self.backgroundRole(), QColor("#000")); p.setColor(self.foregroundRole(), QColor("#FFF")); self.setPalette(p)
        self.setStyleSheet("QGroupBox { border: none; margin: 0px; padding: 0px; } QGroupBox#LeftBox, QGroupBox#CenterBox, QGroupBox#RightBox { background-color: #FFF; }")
        
        self.createAllWidgets(); self.createTopGroupBox(); self.createLeftGroupBox(); self.createCenterGroupBox(); self.createRightGroupBox()
        mainLayout = QGridLayout(); mainLayout.setContentsMargins(0, 0, 0, 0); mainLayout.setSpacing(0); self.setLayout(mainLayout)
        mainLayout.addWidget(self.topGroupBox, 0, 0, 1, 3); mainLayout.addWidget(self.leftGroupBox, 1, 0, 1, 1)
        mainLayout.addWidget(self.centerGroupBox, 1, 1, 1, 1); mainLayout.addWidget(self.rightGroupBox, 1, 2, 1, 1)
        mainLayout.setColumnStretch(0, 3); mainLayout.setColumnStretch(1, 2); mainLayout.setColumnStretch(2, 3)
        mainLayout.setRowStretch(0, 1); mainLayout.setRowStretch(1, 1); mainLayout.setRowStretch(2, 0)
        self._last_gopro_val = -1

    def updateGoProBattery(self, value: int):
        if self._last_gopro_val == value: return
        self._last_gopro_val = value
        c = "#0F0" if value > 50 else "#FF0" if value > 20 else "#F00"
        self.goproLabel.updateValueLabel(f"{value}%"); self.goproLabel.valueLabel.setStyleSheet(f"color: {c}; font-size: 30px; font-weight: bold;")

    def handle_input(self, input_type: str) -> bool: return False

    def updateDashboard(self, info: DashMachineInfo, fuel: float, tpms: dict):
        self.rpmLightBar.updateRpmBar(info.rpm); self.rpmLabel.updateRpmLabel(info.rpm); self.gearLabel.updateGearLabel(info.gearVoltage.gearType)
        self.waterTempTitleValueBox.updateTempValueLabel(info.waterTemp); self.waterTempTitleValueBox.updateWaterTempWarning(info.waterTemp)
        self.oilTempTitleValueBox.updateTempValueLabel(info.oilTemp); self.oilTempTitleValueBox.updateOilTempWarning(info.oilTemp)
        self.opsBar.updatePedalBar(info.oilPress.oilPress)
        self.fanSwitchStateTitleValueBox.updateBoolValueLabel(info.fanEnabled); self.fanSwitchStateTitleValueBox.updateFanWarning(info.fanEnabled)
        self.brakeBiasTitleValueBox.updateValueLabel(info.brakePress.bias); self.tpsTitleValueBox.updateValueLabel(info.throttlePosition)
        self.bpsFTitleValueBox.updateValueLabel(info.brakePress.front); self.bpsRTitleValueBox.updateValueLabel(info.brakePress.rear)
        self.batteryIconValueBox.updateBatteryValueLabel(info.batteryVoltage); self.fuelcaluculatorIconValueBox.updateFuelPercentLabel(fuel)

        if getattr(info, "isRaceFinished", False):
            self.lapTimeBox.updateValueLabel("FINISH"); self.lapTimeBox.valueLabel.setStyleSheet("font-weight: bold; color: #FF00FF; background-color: #000;")
        else:
            self.lapTimeBox.updateValueLabel(format_lap_time(info.currentLapTime)); self.lapTimeBox.valueLabel.setStyleSheet("font-weight: bold; color: #FFF; background-color: #000;")

        self.lapCountBox.updateValueLabel(info.lapCount); self.deltaBox.updateDelta(info.lapTimeDiff)
        
        self.tpms_fl.updateTemperature(tpms.get("FL", {}).get("temp_c")); self.tpms_fl.updatePressure(tpms.get("FL", {}).get("pressure_kpa"))
        self.tpms_fr.updateTemperature(tpms.get("FR", {}).get("temp_c")); self.tpms_fr.updatePressure(tpms.get("FR", {}).get("pressure_kpa"))
        self.tpms_rl.updateTemperature(tpms.get("RL", {}).get("temp_c")); self.tpms_rl.updatePressure(tpms.get("RL", {}).get("pressure_kpa"))
        self.tpms_rr.updateTemperature(tpms.get("RR", {}).get("temp_c")); self.tpms_rr.updatePressure(tpms.get("RR", {}).get("pressure_kpa"))

    def createAllWidgets(self):
        self.rpmLabel = RpmLabel(); self.rpmLabel.setStyleSheet("border: none; border-radius: 0px; font-weight: bold; color: #FFF; background-color: #000")
        self.gearLabel = GearLabel()
        self.waterTempTitleValueBox = TitleValueBox("Water Temp"); self.oilTempTitleValueBox = TitleValueBox("Oil Temp")
        self.fanSwitchStateTitleValueBox = TitleValueBox("Fan Switch")
        self.switchStateRemiderLabel = TitleValueBox("SWITCH CHECK! \n1. Fan \n2. TPS MAX"); self.switchStateRemiderLabel.titleLabel.setAlignment(QtCore.Qt.AlignVCenter); self.switchStateRemiderLabel.titleLabel.setFontScale(0.25)
        self.tpsTitleValueBox = TitleValueBox("TPS"); self.bpsFTitleValueBox = TitleValueBox("BPS F"); self.bpsRTitleValueBox = TitleValueBox("BPS R"); self.brakeBiasTitleValueBox = TitleValueBox("Brake\nBias F%")
        self.opsBar = PedalBar("#F00", 300)
        self.batteryIconValueBox = IconValueBox(); self.fuelcaluculatorIconValueBox = IconValueBox(); self.lapCountLabel = IconValueBox()
        self.tpms_fl = TpmsBox(""); self.tpms_fr = TpmsBox(""); self.tpms_rl = TpmsBox(""); self.tpms_rr = TpmsBox("")
        self.lapTimeBox = TitleValueBox("Lap Time"); self.lapTimeBox.valueLabel.setFontScale(0.55)
        self.lapCountBox = TitleValueBox("Lap"); self.deltaBox = DeltaBox("Delta"); self.goproLabel = TitleValueBox("GoPro Bat")

    def createTopGroupBox(self):
        self.topGroupBox = QGroupBox(); self.topGroupBox.setMaximumHeight(60)
        layout = QGridLayout(); self.rpmLightBar = RpmLightBar(); layout.addWidget(self.rpmLightBar, 0, 0); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        self.topGroupBox.setLayout(layout)

    def createLeftGroupBox(self):
        self.leftGroupBox = QGroupBox(); self.leftGroupBox.setAttribute(QtCore.Qt.WA_StyledBackground, True); self.leftGroupBox.setObjectName("LeftBox")
        layout = QGridLayout()
        layout.addWidget(self.lapTimeBox, 0, 0, 1, 2); layout.addWidget(self.waterTempTitleValueBox, 1, 0); layout.addWidget(self.oilTempTitleValueBox, 1, 1)
        layout.addWidget(self.batteryIconValueBox, 2, 0, 1, 2); layout.addWidget(self.fuelcaluculatorIconValueBox, 3, 0, 1, 2)
        layout.setRowStretch(0, 1); layout.setRowStretch(1, 1); layout.setRowStretch(2, 1); layout.setRowStretch(3, 1); layout.setContentsMargins(2, 2, 2, 2); layout.setSpacing(2)
        self.leftGroupBox.setLayout(layout)

    def createCenterGroupBox(self):
        self.centerGroupBox = QGroupBox(); self.centerGroupBox.setAttribute(QtCore.Qt.WA_StyledBackground, True); self.centerGroupBox.setObjectName("CenterBox")
        layout = QGridLayout()
        layout.addWidget(self.gearLabel, 0, 0, 1, 3, QtCore.Qt.AlignTop); layout.addWidget(self.rpmLabel, 1, 0, 1, 3)
        layout.addWidget(self.tpsTitleValueBox, 2, 0, 1, 3); layout.addWidget(self.opsBar, 3, 0, 1, 3)
        layout.setRowStretch(0, 15); layout.setRowStretch(1, 3); layout.setRowStretch(2, 2); layout.setRowStretch(3, 2); layout.setContentsMargins(2, 2, 2, 2); layout.setSpacing(2)
        self.centerGroupBox.setLayout(layout)

    def createRightGroupBox(self):
        self.rightGroupBox = QGroupBox(); self.rightGroupBox.setAttribute(QtCore.Qt.WA_StyledBackground, True); self.rightGroupBox.setObjectName("RightBox")
        tpmsGridGroup = QGroupBox(); tpmsGridGroup.setObjectName("TpmsGridGroup"); tpmsGridGroup.setStyleSheet("QGroupBox#TpmsGridGroup { background-color: #FFF; border: none; margin: 0px; padding: 0px; }"); tpmsGridGroup.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        tpmsLayout = QGridLayout(); tpmsLayout.setContentsMargins(0, 0, 0, 0); tpmsLayout.setSpacing(2)
        tpmsLayout.addWidget(self.tpms_fl, 0, 0); tpmsLayout.addWidget(self.tpms_fr, 0, 1); tpmsLayout.addWidget(self.tpms_rl, 1, 0); tpmsLayout.addWidget(self.tpms_rr, 1, 1)
        tpmsGridGroup.setLayout(tpmsLayout)
        mainLayout = QGridLayout(); mainLayout.setContentsMargins(2, 2, 2, 2); mainLayout.setSpacing(2)
        lapInfoContainer = QWidget(); lapInfoContainer.setObjectName("LapInfoContainer"); lapInfoContainer.setStyleSheet("QWidget#LapInfoContainer { background-color: #FFF; }"); lapInfoContainer.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        lapInfoLayout = QGridLayout(); lapInfoLayout.setContentsMargins(0, 0, 0, 0); lapInfoLayout.setSpacing(2)
        lapInfoLayout.addWidget(self.deltaBox, 0, 0); lapInfoLayout.addWidget(self.lapCountBox, 1, 0)
        lapInfoContainer.setLayout(lapInfoLayout)
        mainLayout.addWidget(lapInfoContainer, 0, 0); mainLayout.addWidget(tpmsGridGroup, 1, 0)
        mainLayout.setRowStretch(0, 3); mainLayout.setRowStretch(1, 6)
        self.rightGroupBox.setLayout(mainLayout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space: self.requestSetStartLine.emit()
        else: super().keyPressEvent(event)