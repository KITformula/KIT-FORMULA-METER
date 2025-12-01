from src.telemetry.google_sheets_sender import GoogleSheetsSender
from src.telemetry.mqtt_sender import MqttTelemetrySender
from src.logger.csv_logger import CsvLogger
from src.mileage.mileage_tracker import MileageTracker
import logging

logger = logging.getLogger(__name__)

class TelemetryService:
    def __init__(self):
        # スプレッドシート名を "KIT_FORMULA_Log_2026" に設定
        self.sender = GoogleSheetsSender(
            json_keyfile="service_account.json", spreadsheet_name="KIT_FORMULA_Log_2026"
        )
        
        # MQTT送信機の初期化と開始
        self.mqtt_sender = MqttTelemetrySender()
        self.mqtt_sender.start()

        self.logger = CsvLogger(base_dir="logs")
        self.mileage_tracker = MileageTracker()
        self.last_processed_lap = 0

    def process(self, dash_info, fuel_percent, tpms_data, gps_data):
        # 1. MQTT送信 (常時実行)
        self.mqtt_sender.send(dash_info, fuel_percent, tpms_data)

        # 2. CSVログ記録 (RPM 500以上で記録)
        if dash_info.rpm >= 500:
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

        # 3. Google Sheets送信 (ラップ更新時のみ)
        # デバッグ: ラップカウントの変化を監視
        if dash_info.lapCount != self.last_processed_lap:
            logger.debug(f"Lap changed: {self.last_processed_lap} -> {dash_info.lapCount}")

        if dash_info.lapCount > self.last_processed_lap:
            # 1周目完了(lapCount=2になった瞬間)から送信開始
            if dash_info.lapCount > 1:
                print(
                    f"★ Lap Update Detected: {self.last_processed_lap} -> {dash_info.lapCount}. Sending to Sheets..."
                )
                self.sender.send(dash_info, fuel_percent, tpms_data)
            else:
                print(f"★ Lap Update Detected (First Lap): {dash_info.lapCount}. Not sending yet.")
            
            self.last_processed_lap = dash_info.lapCount

        # 4. 走行距離積算
        session_km = gps_data.get("total_distance_km", 0.0)
        self.mileage_tracker.update(session_km)

    def save_mileage(self):
        self.mileage_tracker.save()

    def stop(self):
        if self.logger.is_active:
            self.logger.stop()
        self.sender.stop()
        self.mqtt_sender.stop()