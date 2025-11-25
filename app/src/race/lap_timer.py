import math
import time
import logging
import random
from src.models.models import DashMachineInfo
from src.util import config

logger = logging.getLogger(__name__)

class LapTimer:
    """
    GPS座標を受け取り、ラップタイムの計測と通過判定を行う専門クラス。
    """

    def __init__(self):
        # スタートライン座標
        self.target_lat = None
        self.target_lon = None
        
        # 状態管理
        self.lap_count = 0
        self.current_lap_start_time = 0.0
        self.previous_lap_time = 0.0
        self.prev_gps_lat = None
        self.prev_gps_lon = None
        
        # タイマーが動いているかどうか
        self.is_timer_running = False
        
        # ゾーン判定フラグ (初期値はTrue=コース外/未設定)
        # True: コース上（判定エリア外）にいる。次にエリアに入ったらラップ計測。
        # False: スタートライン付近（判定エリア内）にいる。まずはエリア外に出るのを待つ。
        self.is_outside_lap_zone = True

        # 設定値 (configから取得)
        self.lap_radius = getattr(config, "GPS_LAP_RADIUS_METERS", 5.0)
        self.lap_cooldown = getattr(config, "GPS_LAP_COOLDOWN_SEC", 10.0)
        
        # ★追加: 設定後に確実にエリアから離れたことを判定するための距離
        # 半径の3倍程度、または20mなど、GPS誤差で誤判定しない十分な距離を設定
        self.departure_distance = max(20.0, self.lap_radius * 3.0)

        # モック用変数
        self.mock_lap_time_elapsed = 0.0
        self.mock_lap_duration = 10.0
        self.mock_best_lap = 60.0

    def set_start_line(self, lat: float, lon: float, dash_info: DashMachineInfo):
        """
        現在の座標をスタートラインとして設定し、スタンバイ状態にする。
        """
        if lat == 0.0 and lon == 0.0:
            print("★ GPS測位が無効なため、スタートラインを設定できません。")
            return

        self.target_lat = lat
        self.target_lon = lon
        self.reset_state(dash_info)
        
        print(f"★ スタートライン設定完了: {lat}, {lon} (通過待ち - {self.departure_distance}m離れるまで待機)")

    def reset_state(self, dash_info: DashMachineInfo):
        """状態のリセット（モック・本番共通）"""
        self.lap_count = 0
        self.previous_lap_time = 0.0
        self.current_lap_start_time = 0.0
        self.is_timer_running = False
        
        # 設定直後は「エリア内」にいるとする
        # これにより、一度大きく離れるまでは通過判定が行われない
        self.is_outside_lap_zone = False
        
        self.prev_gps_lat = self.target_lat
        self.prev_gps_lon = self.target_lon
        self.mock_lap_time_elapsed = 0.0

        # ダッシュボード情報リセット
        dash_info.lapCount = 0
        dash_info.lapTimeDiff = 0.0
        dash_info.currentLapTime = 0.0

    def update(self, current_gps_data: dict, dash_info: DashMachineInfo):
        """
        新しいGPSデータを受け取り、必要に応じてラップタイムを更新する。
        """
        # 1. GPSデータの検証
        lat = current_gps_data.get("latitude", 0.0)
        lon = current_gps_data.get("longitude", 0.0)
        quality = current_gps_data.get("quality", 0)
        status = current_gps_data.get("status", "V")

        is_valid_fix = (quality > 0 or status == "A") and (lat != 0.0 or lon != 0.0)
        
        if not is_valid_fix:
            return

        # 2. リアルタイム経過時間の更新 (タイマー動作中のみ)
        current_time = time.monotonic()
        if self.is_timer_running:
            dash_info.currentLapTime = current_time - self.current_lap_start_time
        else:
            dash_info.currentLapTime = 0.0

        # スタートライン未設定ならここで終了
        if self.target_lat is None:
            self.prev_gps_lat = lat
            self.prev_gps_lon = lon
            return

        # 3. 距離計算 (点と点、および線分と点)
        dist_point = self._calculate_distance_meters(
            self.target_lat, self.target_lon, lat, lon
        )
        
        dist_segment = 10000.0
        if self.prev_gps_lat is not None:
            dist_segment = self._get_distance_point_to_segment_meters(
                self.target_lat, self.target_lon,
                self.prev_gps_lat, self.prev_gps_lon,
                lat, lon
            )
        else:
            dist_segment = dist_point

        # 4. 通過判定ロジック
        
        # ■ ゾーン内にいる（設定直後 or 通過直後）場合
        if not self.is_outside_lap_zone:
            # 確実に離れた（脱出距離を超えた）場合のみ、ゾーン外フラグを立てる
            # GPS誤差によるチャタリング防止のため、判定半径(5m)ではなく、大きめの脱出距離(20m)を使う
            if dist_point > self.departure_distance:
                self.is_outside_lap_zone = True
                # print(f"DEBUG: Zone Departure Detected ({dist_point:.1f}m > {self.departure_distance}m)")

        # ■ ゾーン外にいる（走行中）場合
        else:
            # 「点が円内」または「軌跡が円を通過」したらラップ計測
            is_crossing = (dist_segment <= self.lap_radius)
            
            if is_crossing:
                # パターンA: 計測開始 (1周目のスタート)
                if not self.is_timer_running:
                    self.is_timer_running = True
                    self.current_lap_start_time = current_time
                    self.lap_count = 1
                    dash_info.lapCount = 1
                    dash_info.currentLapTime = 0.0
                    print("★ START LINE CROSSED: Race Timer Started!")
                
                # パターンB: ラップ更新 (2周目以降)
                else:
                    time_since_start = current_time - self.current_lap_start_time
                    # クールダウン時間を超えていればラップ確定
                    if time_since_start > self.lap_cooldown:
                        self._register_lap(time_since_start, dash_info)
                        self.current_lap_start_time = current_time 
                
                # 通過したので「ゾーン内」に戻す
                self.is_outside_lap_zone = False

        # 5. 次回用に座標保存
        self.prev_gps_lat = lat
        self.prev_gps_lon = lon

    def update_mock(self, dash_info: DashMachineInfo):
        """
        デバッグ用: GPSなしでラップタイムをシミュレーションする
        """
        self.mock_lap_time_elapsed += 0.050
        
        if self.is_timer_running:
            dash_info.currentLapTime = self.mock_lap_time_elapsed
        else:
            dash_info.currentLapTime = 0.0

        # 設定された「仮想ラップタイム」を超えたらラップ更新
        if self.mock_lap_time_elapsed >= self.mock_lap_duration:
            if not self.is_timer_running:
                # 最初のスタート
                self.is_timer_running = True
                self.lap_count = 1
                dash_info.lapCount = 1
                dash_info.currentLapTime = 0.0
                self.mock_lap_time_elapsed = 0.0
                print("MOCK: START LINE CROSSED (Timer Started)")
            else:
                # ラップ更新
                lap_time = self.mock_lap_time_elapsed
                self._register_lap(lap_time, dash_info)
                self.mock_lap_time_elapsed = 0.0
            
            self.mock_lap_duration = self.mock_best_lap + random.uniform(-3.0, 3.0)

    def _register_lap(self, lap_time: float, dash_info: DashMachineInfo):
        """ラップ確定時の処理"""
        if self.lap_count > 1:
            dash_info.lapTimeDiff = lap_time - self.previous_lap_time
        else:
            dash_info.lapTimeDiff = 0.0
            
        self.previous_lap_time = lap_time
        self.lap_count += 1
        dash_info.lapCount = self.lap_count
        dash_info.currentLapTime = lap_time 
        
        print(f"LAP {self.lap_count - 1} FINISHED: {lap_time:.2f}s (Diff: {dash_info.lapTimeDiff:+.2f}s)")

    # --- 幾何計算ヘルパー ---
    @staticmethod
    def _calculate_distance_meters(lat1, lon1, lat2, lon2):
        """2点間の距離(m)"""
        R = 6371000.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    @staticmethod
    def _get_distance_point_to_segment_meters(lat_p, lon_p, lat_a, lon_a, lat_b, lon_b):
        """点Pと線分ABの最短距離(m)"""
        METERS_PER_LAT = 111319.9
        meters_per_lon = 111319.9 * math.cos(math.radians(lat_p))

        x_a = (lon_a - lon_p) * meters_per_lon
        y_a = (lat_a - lat_p) * METERS_PER_LAT
        x_b = (lon_b - lon_p) * meters_per_lon
        y_b = (lat_b - lat_p) * METERS_PER_LAT

        dx = x_b - x_a
        dy = y_b - y_a

        if dx == 0 and dy == 0:
            return math.sqrt(x_a**2 + y_a**2)

        t = ((-x_a * dx) + (-y_a * dy)) / (dx*dx + dy*dy)
        t = max(0.0, min(1.0, t))

        closest_x = x_a + t * dx
        closest_y = y_a + t * dy

        return math.sqrt(closest_x**2 + closest_y**2)