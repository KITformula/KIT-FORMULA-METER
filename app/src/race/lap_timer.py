import time
import logging
from src.models.models import DashMachineInfo
from src.race.course_manager import CourseManager

logger = logging.getLogger(__name__)


class LapTimer:
    def __init__(self, course_manager: CourseManager):
        self.course_manager = course_manager

        self.lap_count = 0
        self.current_lap_start_time = 0.0
        self.previous_lap_time = 0.0

        # 区間タイム計測用
        self.last_gate_pass_time = 0.0

        # 前周のセクタータイム記録用 {sector_index: time}
        self.previous_lap_sectors = {}
        # 現在周回のセクタータイム一時保存用
        self.current_lap_sectors = {}

        self.prev_gps_lat = None
        self.prev_gps_lon = None

        self.is_timer_running = False
        self.target_sector_index = 0

    def reset_state(self, dash_info: DashMachineInfo):
        self.lap_count = 0
        self.previous_lap_time = 0.0
        self.current_lap_start_time = 0.0
        self.last_gate_pass_time = 0.0
        self.is_timer_running = False
        self.target_sector_index = 0

        self.previous_lap_sectors = {}
        self.current_lap_sectors = {}

        self.prev_gps_lat = None
        self.prev_gps_lon = None

        dash_info.lapCount = 0
        dash_info.lapTimeDiff = 0.0
        dash_info.currentLapTime = 0.0
        dash_info.lastLapTime = 0.0
        dash_info.sector_times = {}
        dash_info.sector_diffs = {}

    def update(self, current_gps_data: dict, dash_info: DashMachineInfo):
        lat = current_gps_data.get("latitude", 0.0)
        lon = current_gps_data.get("longitude", 0.0)
        quality = current_gps_data.get("quality", 0)
        status = current_gps_data.get("status", "V")

        is_valid_fix = (quality > 0 or status == "A") and (lat != 0.0 or lon != 0.0)

        if not is_valid_fix:
            return

        current_time = time.monotonic()

        if self.is_timer_running:
            dash_info.currentLapTime = current_time - self.current_lap_start_time
        else:
            dash_info.currentLapTime = 0.0

        if self.prev_gps_lat is None:
            self.prev_gps_lat = lat
            self.prev_gps_lon = lon
            return

        gate_line = self.course_manager.get_gate_line(self.target_sector_index)

        if gate_line:
            machine_segment = ((self.prev_gps_lat, self.prev_gps_lon), (lat, lon))
            if self._check_intersection(machine_segment, gate_line):
                self._on_gate_passed(self.target_sector_index, current_time, dash_info)

        self.prev_gps_lat = lat
        self.prev_gps_lon = lon

    def _on_gate_passed(
        self, sector_index: int, timestamp: float, dash_info: DashMachineInfo
    ):
        print(f"★ GATE {sector_index} PASSED!")

        if not self.is_timer_running:
            sector_time = 0.0
        else:
            sector_time = timestamp - self.last_gate_pass_time

        self.last_gate_pass_time = timestamp

        # --- スタート/ゴールライン (Index 0) ---
        if sector_index == 0:
            if not self.is_timer_running:
                # スタート
                self.is_timer_running = True
                self.current_lap_start_time = timestamp
                self.lap_count = 1
                dash_info.lapCount = 1

                self.current_lap_sectors = {}
                dash_info.sector_times = {}
                dash_info.sector_diffs = {}
                print("--- RACE START ---")
            else:
                # ゴール (周回完了)
                # 最終セクターを記録 (キーは便宜上0とする)
                self._record_sector_time(0, sector_time, dash_info)

                final_lap_time = timestamp - self.current_lap_start_time
                self._register_lap(final_lap_time, dash_info)

                self.current_lap_start_time = timestamp

                # セクター記録の繰り越し
                self.previous_lap_sectors = self.current_lap_sectors.copy()
                self.current_lap_sectors = {}

            next_index = 1
            if not self.course_manager.get_sector(next_index):
                next_index = 0
            self.target_sector_index = next_index

        else:
            # --- 中間セクター通過 ---
            print(f"Sector {sector_index} Time: {sector_time:.2f}s")
            self._record_sector_time(sector_index, sector_time, dash_info)

            next_index = sector_index + 1
            if not self.course_manager.get_sector(next_index):
                next_index = 0
            self.target_sector_index = next_index

    def _record_sector_time(
        self, sector_idx: int, current_time: float, dash_info: DashMachineInfo
    ):
        self.current_lap_sectors[sector_idx] = current_time
        dash_info.sector_times[sector_idx] = current_time

        if sector_idx in self.previous_lap_sectors:
            prev_time = self.previous_lap_sectors[sector_idx]
            diff = current_time - prev_time
            dash_info.sector_diffs[sector_idx] = diff
        else:
            dash_info.sector_diffs[sector_idx] = 0.0

    def _register_lap(self, lap_time: float, dash_info: DashMachineInfo):
        if self.lap_count > 1:
            dash_info.lapTimeDiff = lap_time - self.previous_lap_time
        else:
            dash_info.lapTimeDiff = 0.0

        self.previous_lap_time = lap_time
        self.lap_count += 1
        dash_info.lapCount = self.lap_count
        dash_info.lastLapTime = lap_time
        print(f"LAP FINISHED: {lap_time:.2f}s")

    @staticmethod
    def _check_intersection(seg1, seg2):
        p1, p2 = seg1
        p3, p4 = seg2

        def ccw(a, b, c):
            return (b[1] - a[1]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[1] - a[1])

        return (ccw(p1, p2, p3) * ccw(p1, p2, p4) < 0) and (
            ccw(p3, p4, p1) * ccw(p3, p4, p2) < 0
        )
