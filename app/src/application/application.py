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

        self.vehicle_service = None
        self.telemetry_service = None
        self.hardware_service = None

        self.latest_tpms_data = {}
        self.current_gps_data = {}
        self.current_lsd_level = 1
        self.update_count = 0

        # ★追加: GoProの状態管理用フラグ
        self.gopro_connected = False
        self.is_auto_recording = False  # RPMトリガーで録画中かどうか

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
        if self.vehicle_service:
            self.vehicle_service.save_fuel_state()
        if self.telemetry_service:
            self.telemetry_service.save_mileage()
            self.telemetry_service.stop()
        if self.hardware_service:
            self.hardware_service.stop()

    def perform_initialization(self):
        logger.info("Starting heavy initialization...")

        self.vehicle_service = VehicleService()
        self.telemetry_service = TelemetryService()
        self.hardware_service = HardwareService()

        self.hardware_service.tpms_updated.connect(self.on_tpms_update)
        self.hardware_service.gps_updated.connect(self.on_gps_update)

        self.vehicle_service.machine.initialise()

        self.window = MainDisplayWindow(self)
        self._connect_gui_signals()

        self.fuel_save_timer.timeout.connect(self.save_states_periodically)
        self.fuel_save_timer.start(config.FUEL_SAVE_INTERVAL_MS)

        # 精密ログ用の専用スレッドを開始する
        self.telemetry_service.start_logging_thread(self.get_current_data)

        self.hardware_service.start()
        logger.info("Initialization complete.")
        self.splash.start_fade_out()

    # ログスレッドから呼ばれるデータ提供メソッド
    def get_current_data(self):
        if not self.vehicle_service:
            return None, 0.0, {}, {}
            
        return (
            self.vehicle_service.dash_info,
            self.vehicle_service.fuel_percentage,
            self.latest_tpms_data,
            self.current_gps_data
        )

    def _connect_gui_signals(self):
        self.window.requestSetStartLine.connect(self.set_start_line)
        self.window.requestResetFuel.connect(self.reset_fuel_integrator)
        self.window.requestLsdChange.connect(self.change_lsd_level)
        self.window.requestSetSector.connect(self.set_sector_point)
        
        self.window.requestSetTargetLaps.connect(self.set_target_laps)
        self.window.requestDriverChange.connect(self.change_driver)
        self.window.requestResetSession.connect(self.reset_session_data)

        self.window.requestGoProConnect.connect(
            self.hardware_service.gopro_worker.start_connection
        )
        self.window.requestGoProDisconnect.connect(
            self.hardware_service.gopro_worker.stop
        )
        self.window.requestGoProRecStart.connect(
            self.hardware_service.gopro_worker.send_command_record_start
        )
        self.window.requestGoProRecStop.connect(
            self.hardware_service.gopro_worker.send_command_record_stop
        )

        self.hardware_service.gopro_worker.status_changed.connect(
            self.window.updateGoProStatus, type=Qt.QueuedConnection
        )
        self.hardware_service.gopro_worker.battery_changed.connect(
            self.window.updateGoProBattery, type=Qt.QueuedConnection
        )
        
        # ★追加: GoProの接続成功/失敗シグナルを受け取る
        self.hardware_service.gopro_worker.connection_success.connect(
            self.on_gopro_connection_status, type=Qt.QueuedConnection
        )

        self.hardware_service.encoder_worker.rotated_cw.connect(self.window.input_cw)
        self.hardware_service.encoder_worker.rotated_ccw.connect(self.window.input_ccw)
        self.hardware_service.encoder_worker.button_pressed.connect(
            self.window.input_enter
        )

    @pyqtSlot()
    def save_states_periodically(self):
        if self.vehicle_service:
            self.vehicle_service.save_fuel_state()
        if self.telemetry_service:
            self.telemetry_service.save_mileage()

    @pyqtSlot()
    def reset_fuel_integrator(self):
        print("★ Fuel Integrator Reset Requested")
        self.vehicle_service.reset_fuel()

    @pyqtSlot(int)
    def set_target_laps(self, laps: int):
        print(f"★ Target Laps Set to: {laps}")
        self.vehicle_service.set_target_laps(laps)

    @pyqtSlot(str)
    def change_driver(self, driver_name: str):
        print(f"★ Driver Changed: {driver_name}")
        if self.vehicle_service and self.vehicle_service.dash_info:
            self.vehicle_service.dash_info.driver = driver_name

    @pyqtSlot()
    def reset_session_data(self):
        print("★ Session Data Reset Requested")
        self.vehicle_service.lap_timer.reset_state(self.vehicle_service.dash_info)

    @pyqtSlot()
    def set_start_line(self):
        lat = self.current_gps_data.get("latitude")
        lon = self.current_gps_data.get("longitude")
        heading = self.current_gps_data.get("heading", 0.0)

        if lat is None or lon is None:
            print("Error: GPS coordinates are None. Cannot set start line.")
            return

        self.vehicle_service.course_manager.set_sector_point(0, lat, lon, heading)
        self.vehicle_service.lap_timer.reset_state(self.vehicle_service.dash_info)

    @pyqtSlot(int)
    def set_sector_point(self, sector_index: int):
        lat = self.current_gps_data.get("latitude")
        lon = self.current_gps_data.get("longitude")
        heading = self.current_gps_data.get("heading", 0.0)

        if lat is None or lon is None:
            print(f"Error: GPS coordinates are None. Cannot set Sector {sector_index}.")
            return

        self.vehicle_service.course_manager.set_sector_point(
            sector_index, lat, lon, heading
        )

    @pyqtSlot(dict)
    def on_tpms_update(self, data: dict):
        self.latest_tpms_data.update(data)

    @pyqtSlot(dict)
    def on_gps_update(self, data: dict):
        self.current_gps_data = data
        if self.vehicle_service and hasattr(self.vehicle_service.dash_info, "gpsQuality"):
            self.vehicle_service.dash_info.gpsQuality = data.get("quality", 0)
            self.vehicle_service.update(data)
            
    # ★追加: GoPro接続状態が変わったときのハンドラ
    @pyqtSlot(bool)
    def on_gopro_connection_status(self, connected: bool):
        self.gopro_connected = connected
        print(f"★ GoPro Connection Status: {connected}")
        # 切断された場合は自動録画フラグもリセット
        if not connected:
            self.is_auto_recording = False

    def show_main_window(self):
        if self.window:
            self.window.showFullScreen()
            self.app.processEvents()
        if self.splash:
            self.splash.close()
            self.splash = None

    def onUpdate(self) -> None:
        self.update_count += 1
        if not self.telemetry_service or not self.vehicle_service:
            return

        # CSVログ記録はスレッドに任せるため、ここではMQTT/Sheets/距離積算のみ行う
        self.telemetry_service.process(
            self.vehicle_service.dash_info,
            self.vehicle_service.fuel_percentage,
            self.latest_tpms_data,
            self.current_gps_data,
        )
        
        # --- ★追加: GoPro 自動録画ロジック (RPM連動) ---
        if self.gopro_connected:
            current_rpm = self.vehicle_service.dash_info.rpm
            
            # RPM 500以上になったら録画開始 (まだ自動録画していない場合)
            if current_rpm >= 500 and not self.is_auto_recording:
                print(f"★ Engine Started (RPM {current_rpm}): Auto-Starting GoPro Recording")
                self.hardware_service.gopro_worker.send_command_record_start()
                self.is_auto_recording = True
                
            # RPM 500未満になったら録画停止 (自動録画中だった場合)
            elif current_rpm < 500 and self.is_auto_recording:
                print(f"★ Engine Stopped (RPM {current_rpm}): Auto-Stopping GoPro Recording")
                self.hardware_service.gopro_worker.send_command_record_stop()
                self.is_auto_recording = False
        # ---------------------------------------------

        if self.window is not None:
            daily_km, total_km = self.telemetry_service.mileage_tracker.get_mileage()
            self.window.updateDashboard(
                self.vehicle_service.dash_info,
                self.vehicle_service.fuel_percentage,
                self.latest_tpms_data,
                self.current_gps_data,
                daily_km,
                total_km,
            )

    @pyqtSlot(int)
    def change_lsd_level(self, level: int):
        print(f"★ LSD Level Changed to: {level}")
        self.current_lsd_level = level