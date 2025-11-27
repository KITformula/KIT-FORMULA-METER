from src.telemetry.google_sheets_sender import GoogleSheetsSender
from src.logger.csv_logger import CsvLogger
from src.mileage.mileage_tracker import MileageTracker


class TelemetryService:
    def __init__(self):
        self.sender = GoogleSheetsSender(
            json_keyfile="service_account.json", spreadsheet_name="Formula_Log_2024"
        )
        self.logger = CsvLogger(base_dir="logs")
        self.mileage_tracker = MileageTracker()
        self.last_processed_lap = 0

    def process(self, dash_info, fuel_percent, tpms_data, gps_data):
        # CSV Logging
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

        # Google Sheets Sending
        if dash_info.lapCount > self.last_processed_lap:
            if dash_info.lapCount > 1:
                print(
                    f"★ Lap Update Detected: {self.last_processed_lap} -> {dash_info.lapCount}. Sending to Sheets..."
                )
                self.sender.send(dash_info, fuel_percent, tpms_data)
            self.last_processed_lap = dash_info.lapCount

        # Mileage Tracking
        session_km = gps_data.get("total_distance_km", 0.0)
        self.mileage_tracker.update(session_km)

    def save_mileage(self):
        self.mileage_tracker.save()

    def stop(self):
        if self.logger.is_active:
            self.logger.stop()
        self.sender.stop()
