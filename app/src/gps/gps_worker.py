import datetime
import math
import time
import threading
import subprocess
import serial
import random
from PyQt5.QtCore import QObject, pyqtSignal

# ===============================================
# ヘルパー関数
# ===============================================


def nmea_to_decimal_degrees(nmea_val, direction):
    try:
        if not nmea_val:
            return None
        dot_index = nmea_val.find(".")
        if dot_index == -1:
            return None
        deg_chars_index = dot_index - 2
        degrees = float(nmea_val[:deg_chars_index])
        minutes = float(nmea_val[deg_chars_index:])
        decimal_degrees = degrees + (minutes / 60)
        if direction in ("S", "W"):
            decimal_degrees = -decimal_degrees
        return decimal_degrees
    except ValueError:
        return None


def parse_nmea_time(time_str):
    if not time_str or "." not in time_str:
        return None
    try:
        h = int(time_str[0:2])
        m = int(time_str[2:4])
        s_full = float(time_str[4:])
        s = int(s_full)
        ms = int((s_full - s) * 1_000_000)
        return datetime.time(
            hour=h, minute=m, second=s, microsecond=ms, tzinfo=datetime.timezone.utc
        )
    except Exception:
        return None


def calculate_distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    if (lat1 == 0.0 and lon1 == 0.0) or (lat2 == 0.0 and lon2 == 0.0):
        return 0.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance


def calculate_distance_meters(lat1, lon1, lat2, lon2):
    return calculate_distance_km(lat1, lon1, lat2, lon2) * 1000.0


# ===============================================
# GPS Worker クラス
# ===============================================


class GpsWorker(QObject):
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, port, baudrate, debug_mode=False, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.debug_mode = debug_mode
        self._running = True
        self.ser = None

        self.total_distance_km = 0.0
        self.last_valid_latitude = 0.0
        self.last_valid_longitude = 0.0
        self.is_time_synced = False

        self.last_known_data = {
            "time": None,
            "latitude": 0.0,
            "longitude": 0.0,
            "quality": 0,
            "sats": 0,
            "status": "V",
            "speed_kph": 0.0,
            "heading": 0.0,
            "total_distance_km": 0.0,
        }

    def stop(self):
        self._running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception as e:
                print(f"シリアルポートクローズエラー: {e}")

    def run(self):
        if self.debug_mode:
            self._run_mock()
        else:
            self._run_serial()

    def _run_mock(self):
        """デバッグ用: 円を描いて走行するデータを生成"""
        print("★ GPS Worker: Mock Mode Started")

        # 基準点 (適当なサーキットの座標など)
        center_lat = 35.3700
        center_lon = 138.9285
        radius_meters = 200.0
        speed_kmh = 60.0

        # 角度 (ラジアン)
        angle = 0.0

        # 0.1秒ごとに更新 (10Hz)
        interval = 0.1

        while self._running:
            # 座標計算 (簡易的)
            # 緯度1度≒111km, 経度1度≒91km
            lat_offset = (radius_meters * math.sin(angle)) / 111000.0
            lon_offset = (radius_meters * math.cos(angle)) / 91000.0

            current_lat = center_lat + lat_offset
            current_lon = center_lon + lon_offset

            # 方位計算 (接線方向)
            # 進行方向は反時計回りとする -> 接線角度 = 現在角度 + 90度
            heading_deg = math.degrees(angle) + 90.0
            if heading_deg >= 360:
                heading_deg -= 360

            # データの更新
            self.last_known_data["latitude"] = current_lat
            self.last_known_data["longitude"] = current_lon
            self.last_known_data["heading"] = heading_deg
            self.last_known_data["speed_kph"] = speed_kmh
            self.last_known_data["quality"] = 1  # Fixあり
            self.last_known_data["sats"] = 12
            self.last_known_data["status"] = "A"

            # 距離計算
            dist = (speed_kmh / 3600.0) * interval  # km
            self.total_distance_km += dist
            self.last_known_data["total_distance_km"] = self.total_distance_km

            # 送信
            self.data_received.emit(self.last_known_data.copy())

            # 角度を進める
            # 角速度 w = v / r
            v_ms = speed_kmh / 3.6
            w = v_ms / radius_meters
            angle += w * interval
            if angle > 2 * math.pi:
                angle -= 2 * math.pi

            time.sleep(interval)

        print("GPS Mock Finished")

    def _run_serial(self):
        """本番用: シリアルポートから読み込み (自動再接続機能付き)"""
        print(f"GPS Worker: Starting connection loop for {self.port}...")

        while self._running:
            try:
                # 1. シリアルポートを開く (接続試行)
                self.ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
                print(f"GPS: シリアルポート {self.port} 接続成功。受信開始。")

                # 接続成功したらエラーをクリア通知（必要であれば）
                # self.error_occurred.emit("GPS Connected")

                raw_line_count = 0

                # 2. 読み込みループ (接続が維持されている間)
                while self._running and self.ser.is_open:
                    try:
                        # データ読み込み
                        line = (
                            self.ser.readline().decode("ascii", errors="ignore").strip()
                        )

                        if not line:
                            continue

                        # 最初の数行だけログに出して動作確認しやすくする
                        if raw_line_count < 5:
                            print(f"GPS Raw: {line}")
                            raw_line_count += 1

                        # NMEAフォーマット($GNxxx, $GPxxx)の解析
                        if line.startswith(("$GN", "$GP")):
                            if self.parse_nmea_line(line):
                                self._update_distance_and_emit()

                    except serial.SerialException as se:
                        # 読み込み中の切断エラー等 -> 内部ループを抜けて再接続へ
                        print(f"GPS切断検知 (Read Error): {se}")
                        break
                    except Exception:
                        # パースエラーなどは無視して読み込み継続
                        pass

            except Exception as e:
                # 接続時のエラー (デバイスが見つからない等)
                if self._running:
                    print(f"GPS接続エラー: {e} -> 2秒後に再試行します...")
                    # GUIに頻繁に通知すると重くなるため、printに留めるか、
                    # "Retrying..." と一度だけ送る制御を入れるのがベターです
                    # self.error_occurred.emit(f"GPS Error: {e}")

            finally:
                # 切断処理 (リソース解放)
                if self.ser and self.ser.is_open:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
                self.ser = None

            # 3. 再接続待機 (停止フラグが立っていない場合のみ)
            if self._running:
                time.sleep(2.0)

        print("GPS Worker スレッドを終了します。")

    def _update_distance_and_emit(self):
        """距離計算とシグナル発行（本番用）"""
        current_lat = self.last_known_data.get("latitude", 0.0)
        current_lon = self.last_known_data.get("longitude", 0.0)
        quality = self.last_known_data.get("quality", 0)
        status = self.last_known_data.get("status", "V")

        is_valid = (quality > 0 or status == "A") and (
            current_lat != 0.0 or current_lon != 0.0
        )

        if is_valid:
            if self.last_valid_latitude != 0.0 or self.last_valid_longitude != 0.0:
                diff = calculate_distance_km(
                    self.last_valid_latitude,
                    self.last_valid_longitude,
                    current_lat,
                    current_lon,
                )
                if diff < 0.5:
                    self.total_distance_km += diff

            self.last_valid_latitude = current_lat
            self.last_valid_longitude = current_lon

        self.last_known_data["total_distance_km"] = self.total_distance_km
        self.data_received.emit(self.last_known_data.copy())

    def parse_nmea_line(self, line):
        # (既存のコードと同じ内容)
        try:
            if "$" not in line:
                return False
            sentence_part = line[line.find("$") :]
            parts = sentence_part.split("*")[0].split(",")
            sentence_type = parts[0]

            if sentence_type.endswith("GGA"):
                if len(parts) > 7:
                    time_str = parts[1]
                    lat_str = parts[2]
                    lat_dir = parts[3]
                    lon_str = parts[4]
                    lon_dir = parts[5]
                    q_str = parts[6]
                    sats_str = parts[7]

                    self.last_known_data["time"] = parse_nmea_time(time_str)
                    if lat_str and lon_str:
                        self.last_known_data["latitude"] = nmea_to_decimal_degrees(
                            lat_str, lat_dir
                        )
                        self.last_known_data["longitude"] = nmea_to_decimal_degrees(
                            lon_str, lon_dir
                        )
                    self.last_known_data["quality"] = int(q_str) if q_str else 0
                    self.last_known_data["sats"] = int(sats_str) if sats_str else 0

                    if self.last_known_data["quality"] > 0:
                        self.last_known_data["status"] = "A"
                    else:
                        self.last_known_data["status"] = "V"
                    return True

            elif sentence_type.endswith("RMC"):
                if len(parts) > 9:
                    time_str = parts[1]
                    status_str = parts[2]
                    lat_str = parts[3]
                    lat_dir = parts[4]
                    lon_str = parts[5]
                    lon_dir = parts[6]
                    date_str = parts[9]

                    self.last_known_data["time"] = parse_nmea_time(time_str)
                    self.last_known_data["status"] = status_str
                    if lat_str and lon_str:
                        self.last_known_data["latitude"] = nmea_to_decimal_degrees(
                            lat_str, lat_dir
                        )
                        self.last_known_data["longitude"] = nmea_to_decimal_degrees(
                            lon_str, lon_dir
                        )

                    track_angle = parts[8]
                    if track_angle:
                        self.last_known_data["heading"] = float(track_angle)

                    if status_str == "A" and self.last_known_data["quality"] == 0:
                        self.last_known_data["quality"] = 1
                    elif status_str == "V":
                        self.last_known_data["quality"] = 0

                    if (
                        status_str == "A"
                        and not self.is_time_synced
                        and time_str
                        and date_str
                    ):
                        self._sync_system_time(date_str, time_str)
                    return True

            elif sentence_type.endswith("VTG"):
                if len(parts) > 1:
                    course = parts[1]
                    if course:
                        self.last_known_data["heading"] = float(course)
                if len(parts) > 8:
                    speed = parts[7]
                    if speed:
                        self.last_known_data["speed_kph"] = float(speed)
                    return True

        except Exception:
            pass
        return False

    def _sync_system_time(self, date_str, time_str):
        # (既存のコードと同じ内容、ただしデバッグ時は実行しないガードを入れると良い)
        if self.debug_mode:
            return
        try:
            if len(date_str) == 6:
                day, month, year = date_str[0:2], date_str[2:4], "20" + date_str[4:6]
            else:
                return
            if len(time_str) >= 6:
                hour, minute, second = time_str[0:2], time_str[2:4], time_str[4:6]
            else:
                return

            date_cmd = f"{year}-{month}-{day} {hour}:{minute}:{second}"
            print(f"GPS Sync: {date_cmd}")
            subprocess.run(["sudo", "date", "-u", "-s", date_cmd], check=True)
            self.is_time_synced = True
        except Exception as e:
            print(f"GPS Sync Failed: {e}")
