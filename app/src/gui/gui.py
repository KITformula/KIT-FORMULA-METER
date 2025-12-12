from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QDialog, QGridLayout, QStackedWidget, QApplication

# 分割したファイルのインポート
from src.gui.screens.dashboard import DashboardWidget, WindowListener
from src.gui.screens.menu_main import SettingsScreen
from src.gui.screens.menu_race import RaceMenuScreen, DriverSelectScreen, GpsSetScreen, GpsSectorScreen, TargetLapsScreen
from src.gui.screens.menu_machine import MachineMenuScreen, LSDMenuScreen, FuelResetScreen
from src.gui.screens.menu_device import DeviceMenuScreen, GoProMenuScreen
from src.gui.screens.menu_info import InfoMenuScreen, MileageScreen


class MainDisplayWindow(QDialog):
    # アプリケーションへ通知するシグナル
    requestSetStartLine = pyqtSignal()
    requestResetFuel = pyqtSignal()
    requestGoProConnect = pyqtSignal()
    requestGoProDisconnect = pyqtSignal()
    requestGoProRecStart = pyqtSignal()
    requestGoProRecStop = pyqtSignal()
    requestSetTargetLaps = pyqtSignal(int)
    requestLsdChange = pyqtSignal(int)
    requestSetSector = pyqtSignal(int)
    requestDriverChange = pyqtSignal(str)
    requestResetSession = pyqtSignal()

    def __init__(self, listener: WindowListener):
        super(MainDisplayWindow, self).__init__(None)
        self.resize(800, 480)
        palette = QApplication.palette()
        palette.setColor(self.backgroundRole(), QColor("#000"))
        palette.setColor(self.foregroundRole(), QColor("#FFF"))
        self.setPalette(palette)

        self.listener = listener
        self.stack = QStackedWidget()

        # 1. Dashboard (Main View)
        self.dashboard = DashboardWidget(listener)
        self.dashboard.requestSetStartLine.connect(self.requestSetStartLine.emit)

        # 2. Main Menu
        self.settings = SettingsScreen()
        self.settings.requestOpenRaceMenu.connect(lambda: self.stack.setCurrentWidget(self.race_menu))
        self.settings.requestOpenMachineMenu.connect(lambda: self.stack.setCurrentWidget(self.machine_menu))
        self.settings.requestOpenDeviceMenu.connect(lambda: self.stack.setCurrentWidget(self.device_menu))
        self.settings.requestOpenInfoMenu.connect(lambda: self.stack.setCurrentWidget(self.info_menu))
        self.settings.requestExit.connect(self.return_to_dashboard)

        # 3. Category Menus & Sub Screens
        
        # [RACE SETUP]
        self.race_menu = RaceMenuScreen()
        self.race_menu.requestOpenDriver.connect(lambda: self.stack.setCurrentWidget(self.driver_screen))
        self.race_menu.requestOpenStartLine.connect(lambda: self.stack.setCurrentWidget(self.gps_set_screen))
        self.race_menu.requestOpenSector.connect(lambda: self.stack.setCurrentWidget(self.gps_sector_screen))
        self.race_menu.requestOpenTargetLaps.connect(lambda: self.stack.setCurrentWidget(self.target_laps_screen))
        self.race_menu.requestResetSession.connect(self.requestResetSession.emit)
        self.race_menu.requestBack.connect(self.return_to_settings)

        self.driver_screen = DriverSelectScreen()
        self.driver_screen.driverChanged.connect(self.requestDriverChange.emit)
        self.driver_screen.requestBack.connect(lambda: self.stack.setCurrentWidget(self.race_menu))

        self.gps_set_screen = GpsSetScreen()
        self.gps_set_screen.requestSetLine.connect(self.requestSetStartLine.emit)
        self.gps_set_screen.requestBack.connect(lambda: self.stack.setCurrentWidget(self.race_menu))

        self.gps_sector_screen = GpsSectorScreen()
        self.gps_sector_screen.requestSetSector.connect(self.requestSetSector.emit)
        self.gps_sector_screen.requestBack.connect(lambda: self.stack.setCurrentWidget(self.race_menu))

        self.target_laps_screen = TargetLapsScreen()
        self.target_laps_screen.requestSetLaps.connect(self.requestSetTargetLaps.emit)
        self.target_laps_screen.requestBack.connect(lambda: self.stack.setCurrentWidget(self.race_menu))

        # [MACHINE SETUP]
        self.machine_menu = MachineMenuScreen()
        self.machine_menu.requestOpenLSD.connect(lambda: self.stack.setCurrentWidget(self.lsd_screen))
        self.machine_menu.requestOpenFuel.connect(lambda: self.stack.setCurrentWidget(self.fuel_screen))
        self.machine_menu.requestBack.connect(self.return_to_settings)

        self.lsd_screen = LSDMenuScreen()
        self.lsd_screen.lsdLevelChanged.connect(self.requestLsdChange.emit)
        self.lsd_screen.requestBack.connect(lambda: self.stack.setCurrentWidget(self.machine_menu))

        self.fuel_screen = FuelResetScreen()
        self.fuel_screen.requestReset.connect(self.requestResetFuel.emit)
        self.fuel_screen.requestBack.connect(lambda: self.stack.setCurrentWidget(self.machine_menu))

        # [DEVICES]
        self.device_menu = DeviceMenuScreen()
        self.device_menu.requestOpenGoPro.connect(lambda: self.stack.setCurrentWidget(self.gopro_screen))
        self.device_menu.requestBack.connect(self.return_to_settings)

        self.gopro_screen = GoProMenuScreen()
        self.gopro_screen.requestConnect.connect(self.requestGoProConnect.emit)
        self.gopro_screen.requestDisconnect.connect(self.requestGoProDisconnect.emit)
        self.gopro_screen.requestRecStart.connect(self.requestGoProRecStart.emit)
        self.gopro_screen.requestRecStop.connect(self.requestGoProRecStop.emit)
        self.gopro_screen.requestBack.connect(lambda: self.stack.setCurrentWidget(self.device_menu))

        # [INFO / LOG]
        self.info_menu = InfoMenuScreen()
        self.info_menu.requestOpenMileage.connect(lambda: self.stack.setCurrentWidget(self.mileage_screen))
        self.info_menu.requestBack.connect(self.return_to_settings)

        self.mileage_screen = MileageScreen()
        self.mileage_screen.requestBack.connect(lambda: self.stack.setCurrentWidget(self.info_menu))

        # Stackに追加
        for w in [self.dashboard, self.settings, 
                  self.race_menu, self.driver_screen, self.gps_set_screen, self.gps_sector_screen, self.target_laps_screen,
                  self.machine_menu, self.lsd_screen, self.fuel_screen,
                  self.device_menu, self.gopro_screen,
                  self.info_menu, self.mileage_screen]:
            self.stack.addWidget(w)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        """
        キーボード入力を処理するイベントハンドラ。
        ESCキーが押されたらアプリケーションを終了する。
        """
        if event.key() == Qt.Key_Escape:
            print("ESCキーが押されました。アプリを終了します。")
            self.close()  # ウィンドウを閉じる
        else:
            super().keyPressEvent(event)

    def return_to_settings(self):
        self.stack.setCurrentWidget(self.settings)
    
    def return_to_dashboard(self):
        self.stack.setCurrentWidget(self.dashboard)

    # --- 更新メソッド ---
    def updateGoProStatus(self, text: str):
        self.gopro_screen.update_status(text)

    def updateGoProBattery(self, value: int):
        self.dashboard.updateGoProBattery(value)
        self.gopro_screen.update_battery(value)

    def updateDashboard(self, dashMachineInfo, fuel_percentage, tpms_data, gps_data, daily_km=0.0, total_km=0.0):
        current_widget = self.stack.currentWidget()

        if current_widget == self.dashboard:
            self.dashboard.updateDashboard(dashMachineInfo, fuel_percentage, tpms_data)
        elif current_widget == self.gps_set_screen:
            self.gps_set_screen.update_data(gps_data)
        elif current_widget == self.gps_sector_screen:
            self.gps_sector_screen.update_gps_data(gps_data)
        elif current_widget == self.fuel_screen:
            self.fuel_screen.update_fuel(fuel_percentage)
        elif current_widget == self.mileage_screen:
            self.mileage_screen.update_distance(daily_km, total_km)

    # --- 入力ハンドリング ---
    def input_cw(self): self._dispatch_input("CW")
    def input_ccw(self): self._dispatch_input("CCW")
    def input_enter(self): self._dispatch_input("ENTER")

    def _dispatch_input(self, input_type):
        current_widget = self.stack.currentWidget()
        if hasattr(current_widget, "handle_input"):
            if current_widget.handle_input(input_type): return
        
        # ダッシュボード表示中のみ設定へ
        if input_type in ["CW", "CCW"] and current_widget == self.dashboard:
            self.stack.setCurrentWidget(self.settings)