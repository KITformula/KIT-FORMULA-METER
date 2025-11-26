import time
import logging
import random
from src.models.models import DashMachineInfo
from src.util import config
from src.race.course_manager import CourseManager

logger = logging.getLogger(__name__)

class LapTimer:
    """
    GPS座標を受け取り、CourseManagerが定義するゲートとの交差判定を行って
    ラップタイムを計測するクラス。
    """

    def __init__(self, course_manager: CourseManager):
        self.course_manager = course_manager
        
        # 状態管理
        self.lap_count = 0
        self.current_lap_start_time = 0.0
        self.previous_lap_time = 0.0
        
        self.prev_gps_lat = None
        self.prev_gps_lon = None
        
        self.is_timer_running = False
        
        # 次に通過すべきターゲットセクターのインデックス
        # 0: Start/Finish, 1: Sector1, 2: Sector2...
        self.target_sector_index = 0 
        
        # モック用
        self.mock_lap_time_elapsed = 0.0
        self.mock_lap_duration = 60.0

    def reset_state(self, dash_info: DashMachineInfo):
        """状態のリセット（リセット時やキャリブレーション時に呼ぶ）"""
        self.lap_count = 0
        self.previous_lap_time = 0.0
        self.current_lap_start_time = 0.0
        self.is_timer_running = False
        self.target_sector_index = 0
        
        self.prev_gps_lat = None
        self.prev_gps_lon = None
        self.mock_lap_time_elapsed = 0.0

        # ダッシュボード情報リセット
        dash_info.lapCount = 0
        dash_info.lapTimeDiff = 0.0
        dash_info.currentLapTime = 0.0

    def update(self, current_gps_data: dict, dash_info: DashMachineInfo):
        """
        新しいGPSデータを受け取り、ゲート通過判定を行う。
        """
        # 1. GPSデータの検証
        lat = current_gps_data.get("latitude", 0.0)
        lon = current_gps_data.get("longitude", 0.0)
        quality = current_gps_data.get("quality", 0)
        status = current_gps_data.get("status", "V")

        is_valid_fix = (quality > 0 or status == "A") and (lat != 0.0 or lon != 0.0)
        
        if not is_valid_fix:
            return

        current_time = time.monotonic()

        # 2. リアルタイム経過時間の更新 (タイマー動作中のみ)
        if self.is_timer_running:
            dash_info.currentLapTime = current_time - self.current_lap_start_time
        else:
            dash_info.currentLapTime = 0.0

        # 前回座標がなければ保存して終了
        if self.prev_gps_lat is None:
            self.prev_gps_lat = lat
            self.prev_gps_lon = lon
            return

        # 3. 通過判定: 現在のターゲットゲートを取得
        gate_line = self.course_manager.get_gate_line(self.target_sector_index)
        
        if gate_line:
            # マシンの移動線分
            machine_segment = ((self.prev_gps_lat, self.prev_gps_lon), (lat, lon))
            
            # 線分交差判定
            if self._check_intersection(machine_segment, gate_line):
                self._on_gate_passed(self.target_sector_index, current_time, dash_info)

        # 4. 座標更新
        self.prev_gps_lat = lat
        self.prev_gps_lon = lon

    def _on_gate_passed(self, sector_index: int, timestamp: float, dash_info: DashMachineInfo):
        """ゲート通過時の処理"""
        print(f"★ GATE {sector_index} PASSED!")

        # スタート/ゴールライン (Index 0) の場合
        if sector_index == 0:
            if not self.is_timer_running:
                # 最初のスタート
                self.is_timer_running = True
                self.current_lap_start_time = timestamp
                self.lap_count = 1
                dash_info.lapCount = 1
                print("--- RACE START ---")
            else:
                # 周回完了 (ゴール)
                lap_time = timestamp - self.current_lap_start_time
                self._register_lap(lap_time, dash_info)
                self.current_lap_start_time = timestamp
            
            # 次はセクター1を目指す（もしあれば）
            # なければまた0を目指す（周回）
            next_index = 1
            if not self.course_manager.get_sector(next_index):
                next_index = 0
            self.target_sector_index = next_index

        else:
            # 中間セクター通過
            print(f"Sector {sector_index} Time: {timestamp - self.current_lap_start_time:.2f}s")
            
            # 次のセクターへ。なければ0（ゴール）へ
            next_index = sector_index + 1
            if not self.course_manager.get_sector(next_index):
                next_index = 0
            self.target_sector_index = next_index

    def _register_lap(self, lap_time: float, dash_info: DashMachineInfo):
        if self.lap_count > 1:
            dash_info.lapTimeDiff = lap_time - self.previous_lap_time
        else:
            dash_info.lapTimeDiff = 0.0
            
        self.previous_lap_time = lap_time
        self.lap_count += 1
        dash_info.lapCount = self.lap_count
        dash_info.currentLapTime = lap_time 
        print(f"LAP FINISHED: {lap_time:.2f}s")

    def update_mock(self, dash_info: DashMachineInfo):
        """デバッグ用モック更新"""
        self.mock_lap_time_elapsed += 0.050
        if self.is_timer_running:
            dash_info.currentLapTime = self.mock_lap_time_elapsed
        
        if self.mock_lap_time_elapsed >= self.mock_lap_duration:
            if not self.is_timer_running:
                self.is_timer_running = True
                self.lap_count = 1
                dash_info.lapCount = 1
                self.mock_lap_time_elapsed = 0.0
            else:
                self._register_lap(self.mock_lap_time_elapsed, dash_info)
                self.mock_lap_time_elapsed = 0.0
                self.mock_lap_duration = 60.0 + random.uniform(-2.0, 2.0)

    @staticmethod
    def _check_intersection(seg1, seg2):
        """
        2つの線分が交差しているか判定する (外積を使用)
        seg1: ((x1, y1), (x2, y2)) - マシン軌跡
        seg2: ((x3, y3), (x4, y4)) - ゲート
        ※ここでは x=lat, y=lon として扱う
        """
        p1, p2 = seg1
        p3, p4 = seg2
        
        def ccw(a, b, c):
            return (b[1] - a[1]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[1] - a[1])

        # 交差判定: ccwの符号が異なればまたいでいる
        # p1-p2 に対して p3, p4 が反対側 かつ p3-p4 に対して p1, p2 が反対側
        return (ccw(p1, p2, p3) * ccw(p1, p2, p4) < 0) and \
               (ccw(p3, p4, p1) * ccw(p3, p4, p2) < 0)