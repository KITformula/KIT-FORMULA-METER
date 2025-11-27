import csv
import datetime
import os
import time

class CsvLogger:
    """
    車両データをCSV形式で保存するクラス。
    """

    def __init__(self, base_dir="logs"):
        self.base_dir = base_dir
        self.file = None
        self.writer = None
        self.is_active = False
        self.start_timestamp = 0.0

    def start(self):
        """
        ログ記録を開始する。
        """
        if self.is_active:
            return

        now = datetime.datetime.now()
        
        date_str = now.strftime("%Y-%m-%d")
        log_dir = os.path.join(self.base_dir, date_str)
        os.makedirs(log_dir, exist_ok=True)

        time_str = now.strftime("%H-%M-%S")
        file_path = os.path.join(log_dir, f"{time_str}.csv")

        try:
            self.file = open(file_path, mode='w', newline='', encoding='utf-8')
            self.writer = csv.writer(self.file)
            
            # ★変更: ヘッダーに新しい項目を追加
            self.writer.writerow([
                "Time", "Elapsed", "RPM", 
                "Throttle", "WaterTemp", "OilPress", "Gear", 
                "TPMS_FL", "TPMS_FR", "TPMS_RL", "TPMS_RR"
            ])
            
            self.start_timestamp = time.time()
            
            self.is_active = True
            print(f"Log started: {file_path}")
            
        except OSError as e:
            print(f"Failed to open log file: {e}")

    # ★変更: 引数を増やし、書き込み内容を追加
    # app/src/logger/csv_logger.py

    def log(self, rpm, throttle, water_temp, oil_press, gear, fl_temp, fr_temp, rl_temp, rr_temp):
        """
        1行分のデータを書き込む。
        """
        if not self.is_active or self.writer is None:
            return
        
        now = datetime.datetime.now()
        current_time_str = now.strftime("%H:%M:%S.%f")[:-3]
        elapsed_seconds = time.time() - self.start_timestamp
        
        try:
            self.writer.writerow([
                current_time_str, 
                f"{elapsed_seconds:.3f}", 
                rpm,
                f"{throttle:.1f}",
                water_temp,
                f"{oil_press:.2f}",
                gear,
                f"{fl_temp:.1f}",
                f"{fr_temp:.1f}",
                f"{rl_temp:.1f}",
                f"{rr_temp:.1f}"
            ])
            # ★ 追加: 書き込みを即座にディスクへ反映させる
            self.file.flush() 
            
        except ValueError:
            pass

    def stop(self):
        # (ここは変更なし)
        if not self.is_active:
            return
            
        if self.file:
            self.file.close()
            self.file = None
            self.writer = None
        
        self.is_active = False
        print("Log stopped.")