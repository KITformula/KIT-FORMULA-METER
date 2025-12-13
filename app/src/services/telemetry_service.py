import threading
import time
import logging
from src.telemetry.google_sheets_sender import GoogleSheetsSender
from src.telemetry.mqtt_sender import MqttTelemetrySender
from src.telemetry.plotjuggler_sender import PlotJugglerSender
from src.logger.csv_logger import CsvLogger
from src.mileage.mileage_tracker import MileageTracker

logger = logging.getLogger(__name__)

class TelemetryService:
    def __init__(self):
        self.sender = GoogleSheetsSender(
            json_keyfile="service_account.json", spreadsheet_name="KIT_FORMULA_Log_2026"
        )
        
        # ▼▼▼ MQTT (HiveMQ) の停止 ▼▼▼
        # self.mqtt_sender = MqttTelemetrySender()
        # self.mqtt_sender.start()

        # PlotJuggler送信機の初期化と開始
        self.pj_sender = PlotJugglerSender()
        self.pj_sender.start()

        self.logger = CsvLogger(base_dir="logs")
        self.mileage_tracker = MileageTracker()
        self.last_processed_lap = 0
        
        # ログ用スレッド管理
        self._logging_thread = None
        self._logging_active = False
        self._data_provider = None  # データ取得用関数

    def start_logging_thread(self, data_provider_func):
        """
        精密な50ms周期でログを取るための専用スレッドを開始
        data_provider_func: 最新の (dash_info, fuel, tpms, gps) を返す関数
        """
        if self._logging_active:
            return

        self._data_provider = data_provider_func
        self._logging_active = True
        self._logging_thread = threading.Thread(target=self._logging_loop, daemon=True)
        self._logging_thread.start()
        logger.info("Precision Logging Thread Started")

    def _logging_loop(self):
        """
        ドリフト補正付きの精密ループ (50ms)
        """
        interval = 0.05  # 50ms
        next_tick = time.monotonic() + interval

        while self._logging_active:
            try:
                # 1. データ取得
                if self._data_provider:
                    dash_info, _, tpms_data, _ = self._data_provider()
                    
                    # 2. 記録判定 (RPM 500以上)
                    if dash_info and dash_info.rpm >= 500:
                        if not self.logger.is_active:
                            self.logger.start()

                        fl_temp = tpms_data.get("FL", {}).get("temp_c", 0.0)
                        fr_temp = tpms_data.get("FR", {}).get("temp_c", 0.0)
                        rl_temp = tpms_data.get("RL", {}).get("temp_c", 0.0)
                        rr_temp = tpms_data.get("RR", {}).get("temp_c", 0.0)

                        self.logger.log(
                            rpm=int(dash_info.rpm),
                            throttle=dash_info.throttlePosition,
                            water_temp=int(dash_info.waterTemp),
                            oil_press=dash_info.oilPress.oilPress,
                            gear=int(dash_info.gearVoltage.gearType),
                            fl_temp=fl_temp,
                            fr_temp=fr_temp,
                            rl_temp=rl_temp,
                            rr_temp=rr_temp,
                        )
                    else:
                        if self.logger.is_active:
                            self.logger.stop()

            except Exception as e:
                logger.error(f"Logging thread error: {e}")

            # 3. 時間調整 (ドリフト補正)
            now = time.monotonic()
            sleep_time = next_tick - now

            if sleep_time > 0:
                time.sleep(sleep_time)
                next_tick += interval
            else:
                # 処理落ちした場合は、現在時刻を基準にリセットして遅れを取り戻そうとしない
                next_tick = now + interval

    def process(self, dash_info, fuel_percent, tpms_data, gps_data):
        """
        GUIスレッド(QTimer)から呼ばれる処理。
        ここには「リアルタイム性が重要でない」または「イベント駆動」の処理だけ残す。
        """
        # 1. MQTT送信 (停止中)
        # ▼▼▼ ここもコメントアウトしました ▼▼▼
        # self.mqtt_sender.send(dash_info, fuel_percent, tpms_data)

        # PlotJugglerへの送信 (UDPなので軽量、GUI更新と同じタイミングで送信)
        self.pj_sender.send(dash_info, fuel_percent, tpms_data)

        # 2. Google Sheets送信 (ラップ更新時)
        if dash_info.lapCount < self.last_processed_lap:
            logger.info(f"Session Reset Detected: {self.last_processed_lap} -> {dash_info.lapCount}")
            self.last_processed_lap = dash_info.lapCount
            return

        if dash_info.lapCount > self.last_processed_lap:
            if dash_info.lapCount > 1:
                print(
                    f"★ Lap Update Detected: {self.last_processed_lap} -> {dash_info.lapCount}. Sending to Sheets..."
                )
                self.sender.send(dash_info, fuel_percent, tpms_data)
            else:
                print(f"★ Lap Update Detected (First Lap): {dash_info.lapCount}. Not sending yet.")
            
            self.last_processed_lap = dash_info.lapCount

        # 3. 走行距離積算
        session_km = gps_data.get("total_distance_km", 0.0)
        # ★変更: タイヤ情報を取得して渡す
        current_tire = getattr(dash_info, "tireSet", "Unknown")
        self.mileage_tracker.update(session_km, current_tire)

    def save_mileage(self):
        self.mileage_tracker.save()

    def stop(self):
        # スレッド停止処理
        self._logging_active = False
        if self._logging_thread:
            self._logging_thread.join(timeout=1.0)

        if self.logger.is_active:
            self.logger.stop()
        self.sender.stop()
        
        # ▼▼▼ ここもコメントアウトしました ▼▼▼
        # self.mqtt_sender.stop()
        
        self.pj_sender.stop()