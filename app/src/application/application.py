import logging
import sys
from PyQt5.QtCore import QObject, QTimer, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication

from src.gui.gui import MainDisplayWindow, WindowListener
from src.gui.splash_screen import SplashScreen
from src.util import config


from src.services.vehicle_service import VehicleService
from src.services.telemetry_service import TelemetryService
from src.services.hardware_service import HardwareService

logger = logging.getLogger(__name__)

class AppWindowListener(WindowListener):
    def __init__(self, app_instance):
        self.app = app_instance
    def onUpdate(self):
        self.app.update()

class Application(QObject, WindowListener):
    def __init__(self):
        super().__init__()

        # サービス層の初期化 (これでロジックやデバイス管理を委譲)
        self.vehicle_service = VehicleService()
        self.telemetry_service = TelemetryService()
        self.hardware_service = HardwareService()

        self.latest_tpms_data = {}
        self.current_gps_data = {}
        self.current_lsd_level = 1
        self.update_count = 0

        # Connect signals from HardwareService
        self.hardware_service.tpms_updated.connect(self.on_tpms_update)
        self.hardware_service.gps_updated.connect(self.on_gps_update)

        if config.debug:
            print("★ App: DEBUG Mode (GPS Mock Enabled)")
        else:
            print("★ App: PROD Mode (Real GPS Enabled)")

        self.app: QApplication = None
        self.splash: SplashScreen = None
        self.window: MainDisplayWindow = None
        self.fuel_save_timer = QTimer()

    def initialize(self) -> None:
        self.app = QApplication(sys.argv)
        screen_size = self.app.primaryScreen().size()
        image_path = "src/gui/icons/kitformula2.png"

        self.splash = SplashScreen(image_path, screen_size)
        
        self.splash.ready_for_heavy_init.connect(self.perform_initialization)
        self.splash.fade_out_finished.connect(self.show_main_window)
        self.splash.start()
        self.app.aboutToQuit.connect(self.cleanup)
        sys.exit(self.app.exec_())

    def cleanup(self):
        logger.info("Application shutting down...")
        # 各サービスに終了処理を委譲
        self.vehicle_service.save_fuel_state()
        self.telemetry_service.save_mileage()
        self.telemetry_service.stop()
        self.hardware_service.stop()

    def perform_initialization(self):
        self.vehicle_service.machine.initialise()
        
        self.window = MainDisplayWindow(self)
        self._connect_gui_signals()
        
        self.fuel_save_timer.timeout.connect(self.save_states_periodically)
        self.fuel_save_timer.start(config.FUEL_SAVE_INTERVAL_MS)

        self.hardware_service.start()
        self.splash.start_fade_out()

    def _connect_gui_signals(self):
        # GUIからのリクエストを適切なサービスメソッドに接続
        self.window.requestSetStartLine.connect(self.set_start_line)
        self.window.requestResetFuel.connect(self.reset_fuel_integrator)
        self.window.requestLapTimeSetup.connect(self.setup_lap_time)
        self.window.requestLsdChange.connect(self.change_lsd_level)
        self.window.requestSetSector.connect(self.set_sector_point)
        
        # GoPro操作 (HardwareServiceの中のWorkerにアクセス)
        # ※より厳密には HardwareService に start_gopro_connection() 等を作るのが理想だが、現状はこれでOK
        self.window.requestGoProConnect.connect(self.hardware_service.gopro_worker.start_connection)
        self.window.requestGoProDisconnect.connect(self.hardware_service.gopro_worker.stop)
        self.window.requestGoProRecStart.connect(self.hardware_service.gopro_worker.send_command_record_start)
        self.window.requestGoProRecStop.connect(self.hardware_service.gopro_worker.send_command_record_stop)
        
        self.hardware_service.gopro_worker.status_changed.connect(self.window.updateGoProStatus, type=Qt.QueuedConnection)
        self.hardware_service.gopro_worker.battery_changed.connect(self.window.updateGoProBattery, type=Qt.QueuedConnection)

        self.hardware_service.encoder_worker.rotated_cw.connect(self.window.input_cw)
        self.hardware_service.encoder_worker.rotated_ccw.connect(self.window.input_ccw)
        self.hardware_service.encoder_worker.button_pressed.connect(self.window.input_enter)

    @pyqtSlot()
    def save_states_periodically(self):
        self.vehicle_service.save_fuel_state()
        self.telemetry_service.save_mileage()

    @pyqtSlot()
    def reset_fuel_integrator(self):
        print("★ Fuel Integrator Reset Requested")
        self.vehicle_service.reset_fuel()
        print(f"-> Fuel reset to {self.vehicle_service.tank_capacity_ml} ml")

    @pyqtSlot()
    def setup_lap_time(self):
        print("★ Lap Time Setup Requested")

    @pyqtSlot()
    def set_start_line(self):
        lat = self.current_gps_data.get("latitude", 0.0)
        lon = self.current_gps_data.get("longitude", 0.0)
        if config.debug: print(f"MOCK: キャリブレーション ({lat}, {lon})")
        self.vehicle_service.course_manager.calibrate_position(lat, lon)
        self.vehicle_service.lap_timer.reset_state(self.vehicle_service.dash_info)

    @pyqtSlot(int)
    def set_sector_point(self, sector_index: int):
        internal_index = sector_index - 1
        lat = self.current_gps_data.get("latitude", 0.0)
        lon = self.current_gps_data.get("longitude", 0.0)
        heading = self.current_gps_data.get("heading", 0.0)
        print(f"Registering Sector {sector_index}: {lat}, {lon}, {heading}")
        self.vehicle_service.course_manager.set_sector_point(internal_index, lat, lon, heading)

    @pyqtSlot(dict)
    def on_tpms_update(self, data: dict):
        self.latest_tpms_data.update(data)

    @pyqtSlot(dict)
    def on_gps_update(self, data: dict):
        self.current_gps_data = data
        # GPS品質情報の更新
        if hasattr(self.vehicle_service.dash_info, "gpsQuality"):
            self.vehicle_service.dash_info.gpsQuality = data.get("quality", 0)
        
        # VehicleServiceにデータ更新を依頼 (LapTimerなどが動く)
        self.vehicle_service.update(data)

    def show_main_window(self):
        if self.window:
            self.window.showFullScreen()
            self.app.processEvents()
        if self.splash:
            self.splash.close()
            self.splash = None

    def onUpdate(self) -> None:
        self.update_count += 1
        
        # テレメトリサービスに「現在の状態」を渡して、送信やログ記録を判断・実行してもらう
        self.telemetry_service.process(
            self.vehicle_service.dash_info,
            self.vehicle_service.fuel_percentage,
            self.latest_tpms_data,
            self.current_gps_data
        )

        # GUIの更新
        if self.window is not None:
            daily_km, total_km = self.telemetry_service.mileage_tracker.get_mileage()

            self.window.updateDashboard(
                self.vehicle_service.dash_info,
                self.vehicle_service.fuel_percentage,
                self.latest_tpms_data,
                self.current_gps_data,
                daily_km, 
                total_km
            )
    
    # ★修正2: 不要になった save_fuel_state(self) メソッドを削除しました
    # 既に save_states_periodically が vehicle_service 経由で呼んでいるため不要です。

    @pyqtSlot(int)
    def change_lsd_level(self, level: int):
        print(f"★ LSD Level Changed to: {level}")
        self.current_lsd_level = level