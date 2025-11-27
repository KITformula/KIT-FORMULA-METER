import logging
import threading
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from src.models.models import DashMachineInfo
from src.telemetry.sender_interface import TelemetrySender

logger = logging.getLogger(__name__)

class GoogleSheetsSender(TelemetrySender):
    def __init__(self, json_keyfile="service_account.json", spreadsheet_name="Formula_Log_2024"):
        self.json_keyfile = json_keyfile
        self.spreadsheet_name = spreadsheet_name
        self.client = None
        self.sheet = None
        self._connect()

    def _connect(self):
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_keyfile, scope)
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open(self.spreadsheet_name).sheet1
            logger.info("Google Sheets Connected.")
        except Exception as e:
            logger.error(f"Google Sheets Connection Failed: {e}")

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def send(self, info: DashMachineInfo, fuel_percent: float, tpms_data: dict) -> None:
        """
        Application側でラップ更新検知後に呼ばれる想定
        """
        # まだラップが完了していない（1周目以下）の場合はデータがないのでガード
        finished_lap_num = info.lapCount - 1
        if finished_lap_num < 1:
            return

        # データを確定させて別スレッドへ
        data_snapshot = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "lap": finished_lap_num,
            "total_time": info.lastLapTime,
            "sector_times": info.sector_times.copy(),
            "sector_diffs": info.sector_diffs.copy()
        }
        
        # 書き込み処理をバックグラウンドで開始
        threading.Thread(target=self._write_row, args=(data_snapshot,)).start()

    def _write_row(self, data):
        try:
            if self.client is None:
                self._connect()

            row_data = [
                data["timestamp"],
                data["lap"],
                f"{data['total_time']:.3f}" if data['total_time'] else ""
            ]

            # --- ★修正箇所: 並び順の制御 ---
            # 通常のソートだと 0 (Final) が最初に来てしまうため、
            # 0 以外のキーをソートした後、0 があれば最後に付け足すロジックにする
            all_keys = list(data["sector_times"].keys())
            sorted_keys = sorted([k for k in all_keys if k != 0])
            
            if 0 in all_keys:
                sorted_keys.append(0) # Finalを最後に追加

            # データの追加
            for idx in sorted_keys:
                # Time
                time_val = data["sector_times"][idx]
                row_data.append(f"{time_val:.3f}")
                
                # Diff
                if idx in data["sector_diffs"]:
                    diff_val = data["sector_diffs"][idx]
                    row_data.append(f"{diff_val:+.3f}")
                else:
                    row_data.append("")

            # ヘッダー自動生成 (初回のみ)
            if self.sheet and not self.sheet.acell('A1').value:
                headers = ["Time", "Lap", "Total"]
                for idx in sorted_keys:
                    name = "Final" if idx == 0 else f"S{idx}"
                    headers.extend([name, f"{name}_Diff"])
                self.sheet.append_row(headers)

            if self.sheet:
                self.sheet.append_row(row_data)
                logger.info(f"Logged to Sheet: Lap {data['lap']}")
            
        except Exception as e:
            logger.error(f"Sheet Write Error: {e}")
            self.client = None