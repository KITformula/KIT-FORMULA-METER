import logging
import sys
import threading

from PyQt5.QtCore import QObject, QTimer, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication

from src.fuel.fuel_calculator import FuelCalculator
from src.race.lap_timer import LapTimer
from src.race.course_manager import CourseManager
from src.gui.gui import MainDisplayWindow, WindowListener
from src.gui.splash_screen import SplashScreen
from src.machine.machine import Machine
from src.logger.csv_logger import CsvLogger

# ★変更: MQTTをやめてGoogle Sheets Senderを使う
# from src.telemetry.mqtt_sender import MqttTelemetrySender
from src.telemetry.google_sheets_sender import GoogleSheetsSender

from src.telemetry.sender_interface import TelemetrySender
from src.tpms.tpms_worker import TpmsWorker
from src.util import config
from src.util.fuel_store import FuelStore
from src.mileage.mileage_tracker import MileageTracker
from src.hardware.encoder_worker import EncoderWorker
from src.gopro.gopro_worker import GoProWorker
from src.gps.gps_worker import GpsWorker

logger = logging.getLogger(__name__)

class AppWindowListener(WindowListener):
    def __init__(self, app_instance):
        self.app = app_instance
    def onUpdate(self):
        self.app.update()

class Application(QObject, WindowListener):
    def __init__(self):
        super().__init__()

        # --- 1. 燃料・マシン設定 ---
        self.fuel_store = FuelStore()
        self.tank_capacity_ml = config.INITIAL_FUEL_ML
        current_start_ml = self.fuel_store.load_state() or self.tank_capacity_ml

        self.fuel_calculator = FuelCalculator(
            injector_flow_rate_cc_per_min=config.INJECTOR_FLOW_RATE_CC_PER_MIN,
            num_cylinders=config.NUM_CYLINDERS,
            tank_capacity_ml=self.tank_capacity_ml,
            current_remaining_ml=current_start_ml,
        )
        
        # --- 2. 走行距離の管理 ---
        self.mileage_tracker = MileageTracker()
        
        # --- 3. コース＆ラップタイマー設定 ---
        self.course_manager = CourseManager()
        self.lap_timer = LapTimer(self.course_manager)
        
        self.machine = Machine(self.fuel_calculator)
        self.csv_logger = CsvLogger(base_dir="logs")

        # ★変更: Google Sheets Sender の初期化
        # 名前はご自身のスプレッドシートに合わせて変更してください
        self.telemetry_sender = GoogleSheetsSender(
            json_keyfile="service_account.json",
            spreadsheet_name="Formula_Log_2024"
        )

        self.tpms_worker = TpmsWorker(
            frequency=config.RTL433_FREQUENCY,
            id_map=config.TPMS_ID_MAP,
            debug_mode=config.debug,
        )
        self.latest_tpms_data = {}

        # --- GPS Worker ---
        self.gps_port = getattr(config, "GPS_PORT", "COM6")
        self.gps_baud = getattr(config, "GPS_BAUD", 115200)
        
        self.gps_worker = GpsWorker(
            self.gps_port, 
            self.gps_baud, 
            debug_mode=config.debug
        )
        self.gps_thread = None

        self.gopro_worker = GoProWorker()
        self.current_gps_data = {}
        self.current_lsd_level = 1
        
        # ★追加: アプリ側でラップ更新を検知するための変数
        self.last_processed_lap_count = 0

        if config.debug:
            print("★ App: DEBUG Mode (GPS Mock Enabled)")
        else:
            print("★ App: PROD Mode (Real GPS Enabled)")

        self.app: QApplication = None
        self.splash: SplashScreen = None
        self.window: MainDisplayWindow = None
        self.fuel_save_timer = QTimer()
        self.update_count = 0
        self.encoder_worker = None

    def initialize(self) -> None:
        self.app = QApplication(sys.argv)
        screen_size = self.app.primaryScreen().size()
        image_path = "src/gui/icons/kitformula2.png"

        self.splash = SplashScreen(image_path, screen_size)
        self.tpms_worker.data_updated.connect(self.on_tpms_update)

        if self.gps_worker:
            self.gps_worker.data_received.connect(self.on_gps_update)
            self.gps_worker.error_occurred.connect(lambda err: print(f"GPS Error: {err}"))

        self.splash.ready_for_heavy_init.connect(self.perform_initialization)
        self.splash.fade_out_finished.connect(self.show_main_window)
        self.splash.start()
        self.app.aboutToQuit.connect(self.cleanup)
        sys.exit(self.app.exec_())

    def cleanup(self):
        logger.info("Application shutting down...")
        self.save_fuel_state()
        self.mileage_tracker.save()
        if self.csv_logger.is_active: self.csv_logger.stop()
        if self.tpms_worker: self.tpms_worker.stop()
        if self.telemetry_sender: self.telemetry_sender.stop()
        if self.gps_worker: self.gps_worker.stop()
        if self.encoder_worker: self.encoder_worker.stop()
        if self.gopro_worker: self.gopro_worker.stop()

    def perform_initialization(self):
        self.machine.initialise()
        # 送信機スタート（今回は常時接続しないので中身は空ですが呼んでおく）
        self.telemetry_sender.start()

        self.window = MainDisplayWindow(self)
        
        self.window.requestSetStartLine.connect(self.set_start_line)
        self.window.requestResetFuel.connect(self.reset_fuel_integrator)
        self.window.requestLapTimeSetup.connect(self.setup_lap_time)
        self.window.requestLsdChange.connect(self.change_lsd_level)
        self.window.requestSetSector.connect(self.set_sector_point)
        
        self.window.requestGoProConnect.connect(self.gopro_worker.start_connection)
        self.window.requestGoProDisconnect.connect(self.gopro_worker.stop)
        self.window.requestGoProRecStart.connect(self.gopro_worker.send_command_record_start)
        self.window.requestGoProRecStop.connect(self.gopro_worker.send_command_record_stop)
        
        self.gopro_worker.status_changed.connect(self.window.updateGoProStatus, type=Qt.QueuedConnection)
        self.gopro_worker.battery_changed.connect(self.window.updateGoProBattery, type=Qt.QueuedConnection)

        self.encoder_worker = EncoderWorker(pin_a=27, pin_b=17, pin_sw=22)
        self.encoder_worker.rotated_cw.connect(self.window.input_cw)
        self.encoder_worker.rotated_ccw.connect(self.window.input_ccw)
        self.encoder_worker.button_pressed.connect(self.window.input_enter)

        self.fuel_save_timer.timeout.connect(self.save_states_periodically)
        self.fuel_save_timer.start(config.FUEL_SAVE_INTERVAL_MS)

        self.tpms_worker.start()

        if self.gps_worker:
            self.gps_thread = threading.Thread(target=self.gps_worker.run, daemon=True)
            self.gps_thread.start()

        self.splash.start_fade_out()

    @pyqtSlot()
    def save_states_periodically(self):
        self.save_fuel_state()
        self.mileage_tracker.save()

    @pyqtSlot()
    def reset_fuel_integrator(self):
        print("★ Fuel Integrator Reset Requested")
        # ★修正: セッター経由で値をセットするように変更 (FuelCalculator側の実装に合わせて)
        self.fuel_calculator.remaining_fuel_ml = self.tank_capacity_ml 
        self.save_fuel_state()
        print(f"-> Fuel reset to {self.tank_capacity_ml} ml")

    @pyqtSlot()
    def setup_lap_time(self):
        print("★ Lap Time Setup Requested")

    @pyqtSlot()
    def set_start_line(self):
        lat = self.current_gps_data.get("latitude", 0.0)
        lon = self.current_gps_data.get("longitude", 0.0)
        if config.debug: print(f"MOCK: キャリブレーション ({lat}, {lon})")
        self.course_manager.calibrate_position(lat, lon)
        self.lap_timer.reset_state(self.machine.canMaster.dashMachineInfo)

    @pyqtSlot(int)
    def set_sector_point(self, sector_index: int):
        internal_index = sector_index - 1
        lat = self.current_gps_data.get("latitude", 0.0)
        lon = self.current_gps_data.get("longitude", 0.0)
        heading = self.current_gps_data.get("heading", 0.0)
        print(f"Registering Sector {sector_index}: {lat}, {lon}, {heading}")
        self.course_manager.set_sector_point(internal_index, lat, lon, heading)

    @pyqtSlot(dict)
    def on_tpms_update(self, data: dict):
        self.latest_tpms_data.update(data)

    @pyqtSlot(dict)
    def on_gps_update(self, data: dict):
        self.current_gps_data = data
        if hasattr(self.machine.canMaster.dashMachineInfo, "gpsQuality"):
            self.machine.canMaster.dashMachineInfo.gpsQuality = data.get("quality", 0)
        
        # LapTimer更新
        self.lap_timer.update(data, self.machine.canMaster.dashMachineInfo)

    def show_main_window(self):
        if self.window:
            self.window.showFullScreen()
            self.app.processEvents()
        if self.splash:
            self.splash.close()
            self.splash = None

    def onUpdate(self) -> None:
        self.update_count += 1
        dash_info = self.machine.canMaster.dashMachineInfo
        fuel_percentage = self.fuel_calculator.remaining_fuel_percent
        current_rpm = int(dash_info.rpm)
        
        # CSVロギング
        if current_rpm >= 500:
            if not self.csv_logger.is_active:
                self.csv_logger.start()
            fl_temp = self.latest_tpms_data.get("FL", {}).get("temp_c", 0.0)
            fr_temp = self.latest_tpms_data.get("FR", {}).get("temp_c", 0.0)
            rl_temp = self.latest_tpms_data.get("RL", {}).get("temp_c", 0.0)
            rr_temp = self.latest_tpms_data.get("RR", {}).get("temp_c", 0.0)
            self.csv_logger.log(
                rpm=current_rpm,
                throttle=dash_info.throttlePosition,
                water_temp=int(dash_info.waterTemp),
                oil_press=dash_info.oilPress.oilPress,
                gear=int(dash_info.gearVoltage.gearType),
                fl_temp=fl_temp, fr_temp=fr_temp, rl_temp=rl_temp, rr_temp=rr_temp
            )
        else:
            if self.csv_logger.is_active:
                self.csv_logger.stop()

        # ★修正: Google Sheets 送信 (ラップ確定チェックをここで実施)
        if dash_info.lapCount > self.last_processed_lap_count:
            # 1周目(lapCount=1)は「スタートしただけ」なので送らない
            # 2周目に入った瞬間(lapCount=2)に、1周目のデータを送る
            if dash_info.lapCount > 1:
                print(f"★ Lap Update Detected: {self.last_processed_lap_count} -> {dash_info.lapCount}. Sending to Sheets...")
                self.telemetry_sender.send(
                    info=dash_info,
                    fuel_percent=fuel_percentage,
                    tpms_data=self.latest_tpms_data,
                )
            
            # 処理済みラップ数を更新
            self.last_processed_lap_count = dash_info.lapCount

        if self.window is not None:
            session_km = self.current_gps_data.get("total_distance_km", 0.0)
            self.mileage_tracker.update(session_km)
            daily_km, total_km = self.mileage_tracker.get_mileage()

            self.window.updateDashboard(
                dash_info,
                fuel_percentage,
                self.latest_tpms_data,
                self.current_gps_data,
                daily_km, 
                total_km
            )
        return super().onUpdate()
    
    def save_fuel_state(self):
        current_ml = self.fuel_calculator.remaining_fuel_ml
        self.fuel_store.save_state(current_ml)

    @pyqtSlot(int)
    def change_lsd_level(self, level: int):
        print(f"★ LSD Level Changed to: {level}")
        self.current_lsd_level = level