import logging
import sys
import threading
# import datetime # 削除: ロジック移動のため不要

from PyQt5.QtCore import QObject, QTimer, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication

from src.fuel.fuel_calculator import FuelCalculator
from src.race.lap_timer import LapTimer
from src.gui.gui import MainDisplayWindow, WindowListener
from src.gui.splash_screen import SplashScreen
from src.machine.machine import Machine

from src.logger.csv_logger import CsvLogger
from src.telemetry.mqtt_sender import MqttTelemetrySender
from src.telemetry.sender_interface import TelemetrySender
from src.tpms.tpms_worker import TpmsWorker
from src.util import config
from src.util.fuel_store import FuelStore
# from src.util.distance_store import DistanceStore # 削除: Trackerが持つため不要
from src.mileage.mileage_tracker import MileageTracker # ★追加

from src.hardware.encoder_worker import EncoderWorker
from src.gopro.gopro_worker import GoProWorker

logger = logging.getLogger(__name__)

if not config.debug:
    from src.gps.gps_worker import GpsWorker
else:
    class GpsWorker:
        pass

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
        
        # --- 2. 走行距離の管理 (修正: Trackerを使用) ---
        # ロジックを MileageTracker に委譲することで Application がすっきりしました
        self.mileage_tracker = MileageTracker()
        
        # ラップタイマー
        self.lap_timer = LapTimer()
        
        self.machine = Machine(self.fuel_calculator)

        self.csv_logger = CsvLogger(base_dir="logs")
        self.telemetry_sender: TelemetrySender = MqttTelemetrySender()

        self.tpms_worker = TpmsWorker(
            frequency=config.RTL433_FREQUENCY,
            id_map=config.TPMS_ID_MAP,
            debug_mode=config.debug,
        )
        self.latest_tpms_data = {}

        self.gps_worker: GpsWorker | None = None
        self.gps_thread: threading.Thread | None = None

        self.gopro_worker = GoProWorker()

        self.current_gps_data = {}
        
        # LSDの現在のレベルを保持
        self.current_lsd_level = 1

        if config.debug:
            print("★ GPSワーカーはモックモードで起動します ★")
        else:
            print("★ GPSワーカーは本番モードで起動します ★")
            self.gps_port = getattr(config, "GPS_PORT", "COM6")
            self.gps_baud = getattr(config, "GPS_BAUD", 115200)
            self.gps_worker = GpsWorker(self.gps_port, self.gps_baud)

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

        if not config.debug and self.gps_worker:
            self.gps_worker.data_received.connect(self.on_gps_update)
            self.gps_worker.error_occurred.connect(
                lambda err: print(f"GPS Error: {err}")
            )

        self.splash.ready_for_heavy_init.connect(self.perform_initialization)
        self.splash.fade_out_finished.connect(self.show_main_window)
        self.splash.start()

        self.app.aboutToQuit.connect(self.cleanup)

        sys.exit(self.app.exec_())

    def cleanup(self):
        logger.info("Application shutting down...")
        self.save_fuel_state()
        self.mileage_tracker.save() # ★修正: Trackerに保存を依頼

        if self.csv_logger.is_active:
            self.csv_logger.stop()

        if self.tpms_worker:
            self.tpms_worker.stop()

        if self.telemetry_sender:
            self.telemetry_sender.stop()

        if not config.debug and self.gps_worker:
            self.gps_worker.stop()
            
        if self.encoder_worker:
            self.encoder_worker.stop()
            
        if self.gopro_worker:
            self.gopro_worker.stop()

    def perform_initialization(self):
        self.machine.initialise()
        self.telemetry_sender.start()

        self.window = MainDisplayWindow(self)
        
        self.window.requestSetStartLine.connect(self.set_start_line)
        self.window.requestResetFuel.connect(self.reset_fuel_integrator)
        self.window.requestLapTimeSetup.connect(self.setup_lap_time)
        self.window.requestLsdChange.connect(self.change_lsd_level)
        
        self.window.requestGoProConnect.connect(self.gopro_worker.start_connection)
        self.window.requestGoProDisconnect.connect(self.gopro_worker.stop)
        self.window.requestGoProRecStart.connect(self.gopro_worker.send_command_record_start)
        self.window.requestGoProRecStop.connect(self.gopro_worker.send_command_record_stop)
        
        self.gopro_worker.status_changed.connect(
            self.window.updateGoProStatus, 
            type=Qt.QueuedConnection
        )
        self.gopro_worker.battery_changed.connect(
            self.window.updateGoProBattery,
            type=Qt.QueuedConnection
        )

        self.encoder_worker = EncoderWorker(pin_a=27, pin_b=17, pin_sw=22)
        self.encoder_worker.rotated_cw.connect(self.window.input_cw)
        self.encoder_worker.rotated_ccw.connect(self.window.input_ccw)
        self.encoder_worker.button_pressed.connect(self.window.input_enter)

        # タイマーで燃料と距離を定期保存
        self.fuel_save_timer.timeout.connect(self.save_states_periodically)
        self.fuel_save_timer.start(config.FUEL_SAVE_INTERVAL_MS)

        self.tpms_worker.start()

        if not config.debug and self.gps_worker:
            self.gps_thread = threading.Thread(target=self.gps_worker.run, daemon=True)
            self.gps_thread.start()

        self.splash.start_fade_out()

    @pyqtSlot()
    def save_states_periodically(self):
        """定期的に状態を保存するスロット"""
        self.save_fuel_state()
        self.mileage_tracker.save() # ★修正: Trackerに保存を依頼

    @pyqtSlot()
    def reset_fuel_integrator(self):
        print("★ Fuel Integrator Reset Requested")
        self.fuel_calculator.remaining_fuel_ml = self.tank_capacity_ml
        self.save_fuel_state()
        print(f"-> Fuel reset to {self.tank_capacity_ml} ml")

    @pyqtSlot()
    def setup_lap_time(self):
        print("★ Lap Time Setup Requested")

    @pyqtSlot()
    def set_start_line(self):
        # LapTimerクラスに処理を委譲
        if config.debug:
            print("MOCK: スタートライン設定 (デバッグモード)")
            self.lap_timer.reset_state(self.machine.canMaster.dashMachineInfo)
            return

        lat = self.current_gps_data.get("latitude", 0.0)
        lon = self.current_gps_data.get("longitude", 0.0)
        
        self.lap_timer.set_start_line(lat, lon, self.machine.canMaster.dashMachineInfo)

    @pyqtSlot(dict)
    def on_tpms_update(self, data: dict):
        self.latest_tpms_data.update(data)

    @pyqtSlot(dict)
    def on_gps_update(self, data: dict):
        if config.debug:
            return
        self.current_gps_data = data
        
        if hasattr(self.machine.canMaster.dashMachineInfo, "gpsQuality"):
            self.machine.canMaster.dashMachineInfo.gpsQuality = data.get("quality", 0)
            
        # LapTimerに更新を依頼
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

        if config.debug:
            self.lap_timer.update_mock(dash_info)
            
        current_rpm = int(dash_info.rpm)
        
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
                fl_temp=fl_temp,
                fr_temp=fr_temp,
                rl_temp=rl_temp,
                rr_temp=rr_temp
            )
            
        else:
            if self.csv_logger.is_active:
                self.csv_logger.stop()

        if dash_info.rpm >= 500:
            if self.update_count % 40 == 0:
                logger.debug(f"onUpdate calling send(): RPM={dash_info.rpm}")

            self.telemetry_sender.send(
                info=dash_info,
                fuel_percent=fuel_percentage,
                tpms_data=self.latest_tpms_data,
            )

        if self.window is not None:
            # ★修正: Trackerに計算と取得を依頼
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

    # save_distance_stateメソッドは削除し、mileage_tracker.save()に置き換えました

    @pyqtSlot(int)
    def change_lsd_level(self, level: int):
        print(f"★ LSD Level Changed to: {level}")
        self.current_lsd_level = level