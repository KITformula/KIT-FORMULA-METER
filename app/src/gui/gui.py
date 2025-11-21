# from abc import ABCMeta, abstractmethod


from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QGroupBox,
)

from src.gui.self_defined_widgets import (
    GearLabel,
    IconValueBox,
    # LapTimerLabel,
    PedalBar,
    RpmLabel,
    RpmLightBar,
    TitleValueBox,
    TpmsBox,
)
from src.models.models import (
    DashMachineInfo,
    # Message,
)


class WindowListener:  # (metaclass=ABCMeta):
    # @abstractmethod
    def onUpdate(self) -> None:
        pass


class MainWindow(QDialog):
    requestSetStartLine = pyqtSignal()

    def __init__(self, listener: WindowListener):
        super(MainWindow, self).__init__(None)

        self.resize(800, 480)

        self.listener = listener

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.listener.onUpdate)
        self.timer.start(50)

        palette = QApplication.palette()
        palette.setColor(self.backgroundRole(), QColor("#000"))
        palette.setColor(self.foregroundRole(), QColor("#FFF"))
        self.setPalette(palette)  # 画面背景と文字設定

        self.createAllWidgets()
        self.createTopGroupBox()
        self.createLeftGroupBox()
        self.createCenterGroupBox()
        self.createRightGroupBox()
        # self.createBottomGroupBox()

        mainLayout = QGridLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        self.setLayout(mainLayout)
        mainLayout.addWidget(self.topGroupBox, 0, 0, 1, 3)
        mainLayout.addWidget(self.leftGroupBox, 1, 0, 1, 1)
        mainLayout.addWidget(self.centerGroupBox, 1, 1, 1, 1)
        mainLayout.addWidget(self.rightGroupBox, 1, 2, 1, 1)
        # mainLayout.addWidget(self.bottomGroupBox, 2, 0, 1, 3)

        mainLayout.setColumnStretch(0, 3)
        mainLayout.setColumnStretch(1, 2)
        mainLayout.setColumnStretch(2, 3)
        mainLayout.setRowStretch(0, 1)
        mainLayout.setRowStretch(1, 1)
        mainLayout.setRowStretch(2, 0)

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
        # self.oilPressTitleValueBox.updateOilPressWarning(dashMachineInfo.oilPress)
        # self.messageIconValueBox.updateMessageLabel(message)
        # self.lapTimerLabel.updateLapTimerLabel(message)
        # self.timeIconValueBox.updateTime()
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
        # self.bpsFBar.updatePedalBar(dashMachineInfo.brakePress.front)
        # self.bpsRBar.updatePedalBar(dashMachineInfo.brakePress.rear)
        self.batteryIconValueBox.updateBatteryValueLabel(dashMachineInfo.batteryVoltage)
        self.fuelcaluculatorIconValueBox.updateFuelPercentLabel(fuel_percentage)
        self.lapTimeBox.updateValueLabel(f"{dashMachineInfo.currentLapTime:.2f}")
        self.lapCountBox.updateValueLabel(dashMachineInfo.lapCount)

        # Δタイムの正負で色を変えたり符号をつける
        diff = dashMachineInfo.lapTimeDiff
        sign = "+" if diff > 0 else ""
        self.deltaBox.updateValueLabel(f"{sign}{diff:.2f}")

        # FL (左前)
        fl_data = tpms_data.get("FL", {})  # データがない場合は空の辞書
        self.tpms_fl.updateTemperature(fl_data.get("temp_c"))
        self.tpms_fl.updatePressure(fl_data.get("pressure_kpa"))

        # FR (右前)
        fr_data = tpms_data.get("FR", {})
        self.tpms_fr.updateTemperature(fr_data.get("temp_c"))
        self.tpms_fr.updatePressure(fr_data.get("pressure_kpa"))

        # RL (左後)
        rl_data = tpms_data.get("RL", {})
        self.tpms_rl.updateTemperature(rl_data.get("temp_c"))
        self.tpms_rl.updatePressure(rl_data.get("pressure_kpa"))

        # RR (右後)
        rr_data = tpms_data.get("RR", {})
        self.tpms_rr.updateTemperature(rr_data.get("temp_c"))
        self.tpms_rr.updatePressure(rr_data.get("pressure_kpa"))

    def createAllWidgets(self):
        self.rpmLabel = RpmLabel()
        self.gearLabel = GearLabel()
        # self.lapTimerLabel = LapTimerLabel()

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
        # self.bpsFBar = PedalBar("#F00", 600)
        # self.bpsRBar = PedalBar("#F00", 600)
        self.opsBar = PedalBar("#F00", 300)
        # self.bpsRBar.setInvertedAppearance(True)

        self.batteryIconValueBox = IconValueBox()
        self.fuelcaluculatorIconValueBox = IconValueBox()
        self.lapCountLabel = IconValueBox()
        self.tpms_fl = TpmsBox("FL")
        self.tpms_fr = TpmsBox("FR")
        self.tpms_rl = TpmsBox("RL")
        self.tpms_rr = TpmsBox("RR")

        # 中央用: ラップタイム
        self.lapTimeBox = TitleValueBox("Lap Time")
        self.lapCountBox = TitleValueBox("Lap")
        self.deltaBox = TitleValueBox("Delta")
        # self.timeIconValueBox = IconValueBox("src/gui/icons/Timeicon.png")
        # self.messageIconValueBox = IconValueBox("src/gui/icons/japan.png")
        # self.messageIconValueBox.valueLabel.setAlignment(QtCore.Qt.AlignVCenter)
        # self.messageIconValueBox.layout.setColumnStretch(0, 1)
        # self.messageIconValueBox.layout.setColumnStretch(1, 6)

    # ------------------------------Define Overall Layout Group Box---------------------
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
        # self.leftGroupBox.setStyleSheet("border:0;")
        self.leftGroupBox.setObjectName("LeftBox")
        self.leftGroupBox.setStyleSheet("QGroupBox#LeftBox { border: 2px solid white;}")

        layout = QGridLayout()

        layout.addWidget(self.waterTempTitleValueBox, 0, 1)
        layout.addWidget(self.oilTempTitleValueBox, 1, 1)
        # layout.addWidget(self.oilPressTitleValueBox, 2, 1)
        layout.addWidget(self.batteryIconValueBox, 2, 1)
        layout.addWidget(self.fuelPressIconValueBox, 3, 1)
        # layout.addWidget(self.fanSwitchStateTitleValueBox, 4, 1)
        layout.addWidget(self.fuelcaluculatorIconValueBox, 4, 1)
        # layout.addWidget(self.brakeBiasTitleValueBox, 2, 1)
        # layout.addWidget(self.switchStateRemiderLabel, 5, 1)

        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 1)
        layout.setRowStretch(3, 1)
        layout.setRowStretch(4, 1)
        # layout.setRowStretch(5, 1)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.leftGroupBox.setLayout(layout)

    def createCenterGroupBox(self):
        self.centerGroupBox = QGroupBox()
        self.centerGroupBox.setFlat(True)
        self.centerGroupBox.setStyleSheet("border: 2px solid white;")

        layout = QGridLayout()

        layout.addWidget(self.rpmLabel, 0, 0, 1, 3)
        # Row 1: Gear
        layout.addWidget(self.gearLabel, 1, 0, 1, 3)

        # ★★★ Row 2: Lap Time (Gearの下, TPSの上) ★★★
        layout.addWidget(self.lapTimeBox, 2, 0, 1, 3)

        # Row 3: TPS (元の位置)
        layout.addWidget(self.tpsBar, 3, 1, 1, 2)
        layout.addWidget(self.tpsTitleValueBox, 3, 0, 1, 1)

        # レイアウト比率調整
        layout.setRowStretch(0, 2)
        layout.setRowStretch(1, 10)  # Gearを大きく
        layout.setRowStretch(2, 4)  # LapTime
        layout.setRowStretch(3, 2)  # TPS

        self.centerGroupBox.setLayout(layout)

    def createRightGroupBox(self):
        self.rightGroupBox = QGroupBox()
        self.rightGroupBox.setFlat(True)
        # self.rightGroupBox.setStyleSheet("border:0;")
        self.rightGroupBox.setObjectName("RightBox")
        self.rightGroupBox.setStyleSheet(
            "QGroupBox#RightBox { border: 2px solid white;}"
        )

        tpmsGridGroup = QGroupBox("TPMS")
        tpmsGridGroup.setFlat(True)
        tpmsGridGroup.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFF;")

        # (b) 2x2のグリッドレイアウトを作成
        tpmsLayout = QGridLayout()
        tpmsLayout.setContentsMargins(0, 0, 0, 0)
        tpmsLayout.setSpacing(5)  # ボックス間の隙間

        # 1段目
        tpmsLayout.addWidget(self.tpms_fl, 0, 0)
        tpmsLayout.addWidget(self.tpms_fr, 0, 1)
        # 2段目
        tpmsLayout.addWidget(self.tpms_rl, 1, 0)
        tpmsLayout.addWidget(self.tpms_rr, 1, 1)

        tpmsGridGroup.setLayout(tpmsLayout)  # グループにレイアウトをセット

        mainLayout = QGridLayout()
        mainLayout.setContentsMargins(5, 5, 5, 5)
        mainLayout.setSpacing(5)

        # Row 0: 油圧バー
        mainLayout.addWidget(self.opsBar, 0, 0)

        # ★★★ Row 1: ラップカウントとDelta (油圧の下、TPMSの上) ★★★
        # 横並びにするためのサブレイアウト
        lapInfoLayout = QGridLayout()
        lapInfoLayout.addWidget(self.lapCountBox, 0, 0)
        lapInfoLayout.addWidget(self.deltaBox, 0, 1)

        # サブレイアウトを保持するコンテナWidgetを作る必要があるが、
        # 簡易的に addLayout で追加も可能 (QGridLayoutなら)
        mainLayout.addLayout(lapInfoLayout, 1, 0)

        # Row 2: TPMS Grid
        mainLayout.addWidget(
            tpmsGridGroup, 2, 0
        )  # tpmsGridGroupは既存コードで作成済みとする

        # 比率調整
        mainLayout.setRowStretch(0, 1)  # OPS
        mainLayout.setRowStretch(1, 2)  # Lap info
        mainLayout.setRowStretch(2, 7)  # TPMS

        self.rightGroupBox.setLayout(mainLayout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            # 親(Application)に通知
            self.requestSetStartLine.emit()
        else:
            super().keyPressEvent(event)

    # def createBottomGroupBox(self):
    #     self.bottomGroupBox = QGroupBox()
    #     self.bottomGroupBox.setFlat(True)
    #     self.bottomGroupBox.setStyleSheet("border: 0px;")

    #     layout = QGridLayout()

    #     layout.addWidget(self.batteryIconValueBox, 0, 0)
    #     layout.addWidget(self.messageIconValueBox, 0, 1)
    #     layout.addWidget(self.timeIconValueBox, 0, 2)

    #     layout.setColumnStretch(0, 1)
    #     layout.setColumnStretch(1, 3)
    #     layout.setColumnStretch(2, 1)

    #     layout.setContentsMargins(0, 0, 0, 0)
    #     layout.setSpacing(0)

    #     self.bottomGroupBox.setLayout(layout)
