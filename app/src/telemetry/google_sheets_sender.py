import logging
import threading
import time
import queue
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
        
        self.queue = queue.Queue()
        self.running = True
        
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

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
            return True
        except Exception as e:
            logger.error(f"Google Sheets Connection Failed: {e}")
            self.client = None
            self.sheet = None
            return False

    def start(self) -> None:
        pass

    def stop(self) -> None:
        self.running = False

    def send(self, info: DashMachineInfo, fuel_percent: float, tpms_data: dict) -> None:
        finished_lap_num = info.lapCount - 1
        if finished_lap_num < 1:
            return

        now = datetime.now()
        data_snapshot = {
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "driver": info.driver,
            "tire": getattr(info, "tireSet", "Unknown"), # ★追加
            "lap": finished_lap_num,
            "total_time": info.lastLapTime,
            "sector_times": info.sector_times.copy(),
            "sector_diffs": info.sector_diffs.copy(),
        }

        self.queue.put(data_snapshot)

    def _worker_loop(self):
        logger.info("Sheet Worker Started.")
        
        while self.running:
            try:
                try:
                    data = self.queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                sent_success = False
                while not sent_success and self.running:
                    try:
                        if self.client is None or self.sheet is None:
                            logger.info("Connecting to Google Sheets...")
                            if not self._connect():
                                time.sleep(5)
                                continue

                        if self.sheet is None:
                            logger.error("Sheet object is None. Cannot write.")
                            time.sleep(5)
                            continue

                        total_time_val = round(data['total_time'], 3) if data["total_time"] else ""
                        
                        # ★データ列の構成変更
                        row_data = [
                            data["datetime"],
                            data["driver"],
                            data["tire"], # ★ここにTire列を追加
                            data["lap"],
                            total_time_val,
                        ]

                        all_keys = list(data["sector_times"].keys())
                        int_keys = [k for k in all_keys if isinstance(k, int)]
                        sorted_keys = sorted([k for k in int_keys if k != 0])
                        if 0 in int_keys: sorted_keys.append(0)

                        for idx in sorted_keys:
                            row_data.append(round(data["sector_times"][idx], 3))
                            if idx in data["sector_diffs"]:
                                row_data.append(round(data["sector_diffs"][idx], 3))
                            else:
                                row_data.append("")

                        # ヘッダーチェック（初回のみ）
                        try:
                            if not self.sheet.acell("A1").value:
                                # ★ヘッダーにもTireを追加
                                headers = ["Date", "Driver", "Tire", "Lap", "Total"]
                                for idx in sorted_keys:
                                    name = "Final" if idx == 0 else f"S{idx}"
                                    headers.extend([name, f"{name}_Diff"])
                                self.sheet.insert_row(headers, index=1)
                        except:
                            pass

                        # ★ insert_row で2行目に挿入（上に追加）
                        self.sheet.insert_row(row_data, index=2)
                        
                        logger.info(f"Logged to Sheet (Top): Lap {data['lap']} - SUCCESS")
                        
                        sent_success = True
                        self.queue.task_done()

                    except Exception as e:
                        logger.warning(f"Sheet Write Error: {e}. Retrying in 5s...")
                        self.client = None
                        self.sheet = None
                        time.sleep(5)

            except Exception as e:
                logger.error(f"Worker Loop Error: {e}")