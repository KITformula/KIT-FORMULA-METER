import logging
import threading
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from src.models.models import DashMachineInfo
from src.telemetry.sender_interface import TelemetrySender

logger = logging.getLogger(__name__)


class GoogleSheetsSender(TelemetrySender):
    def __init__(
        self, json_keyfile="service_account.json", spreadsheet_name="KIT_FORMULA_Log_2026"
    ):
        self.json_keyfile = json_keyfile
        self.spreadsheet_name = spreadsheet_name
        self.client = None
        self.sheet = None
        
        try:
            self._connect()
        except Exception as e:
            logger.error(f"Initial Google Sheets Connection Failed: {e}")

    def _connect(self):
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file",
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.json_keyfile, scope
            )
            self.client = gspread.authorize(creds)
            
            self.sheet = self.client.open(self.spreadsheet_name).sheet1
            logger.info(f"Google Sheets '{self.spreadsheet_name}' Connected successfully.")
            
        except Exception as e:
            logger.error(f"Google Sheets Connection Failed: {e}")
            self.client = None
            self.sheet = None

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def send(self, info: DashMachineInfo, fuel_percent: float, tpms_data: dict) -> None:
        finished_lap_num = info.lapCount - 1
        if finished_lap_num < 1:
            return

        now = datetime.now()
        data_snapshot = {
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "driver": info.driver,  # ★追加
            "lap": finished_lap_num,
            "total_time": info.lastLapTime,
            "sector_times": info.sector_times.copy(),
            "sector_diffs": info.sector_diffs.copy(),
        }

        thread = threading.Thread(target=self._write_row_thread, args=(data_snapshot,))
        thread.daemon = True
        thread.start()

    def _write_row_thread(self, data):
        try:
            if self.client is None or self.sheet is None:
                logger.info("Reconnecting to Google Sheets...")
                self._connect()

            if self.sheet is None:
                logger.error("Sheet object is None. Cannot write.")
                return

            total_time_val = round(data['total_time'], 3) if data["total_time"] else ""
            
            # ★修正: 書き込みデータの並び順 (日時 -> ドライバー -> ラップ -> タイム)
            row_data = [
                data["datetime"], # A列
                data["driver"],   # B列: ドライバー名
                data["lap"],      # C列
                total_time_val,   # D列
            ]

            all_keys = list(data["sector_times"].keys())
            int_keys = [k for k in all_keys if isinstance(k, int)]
            sorted_keys = sorted([k for k in int_keys if k != 0])

            if 0 in int_keys:
                sorted_keys.append(0)

            for idx in sorted_keys:
                # Time
                time_val = round(data["sector_times"][idx], 3)
                row_data.append(time_val) 

                # Diff
                if idx in data["sector_diffs"]:
                    diff_val = round(data["sector_diffs"][idx], 3)
                    row_data.append(diff_val)
                else:
                    row_data.append("")

            # ヘッダー生成
            try:
                first_cell = self.sheet.acell("A1").value
                if not first_cell:
                    # ★修正: ヘッダーにDriver追加
                    headers = ["Date", "Driver", "Lap", "Total"]
                    for idx in sorted_keys:
                        name = "Final" if idx == 0 else f"S{idx}"
                        headers.extend([name, f"{name}_Diff"])
                    self.sheet.insert_row(headers, index=1)
                    logger.info("Inserted headers to new sheet.")
            except Exception as header_err:
                logger.warning(f"Header check failed (continuing): {header_err}")

            self.sheet.append_row(row_data)
            logger.info(f"Logged to Sheet: Lap {data['lap']} - SUCCESS")

        except Exception as e:
            logger.error(f"Sheet Write Error: {e}")
            self.client = None
            self.sheet = None