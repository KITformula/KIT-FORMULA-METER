import serial
import datetime
import math
import time
from PyQt5.QtCore import QObject, pyqtSignal

# ===============================================
# ヘルパー関数 (tougou8.py から移植)
# ===============================================

def nmea_to_decimal_degrees(nmea_val, direction):
    """
    NMEA形式(DDMM.MMMMM または DDDMM.MMMMM)を十進度の緯度経度に変換する
    """
    try:
        if not nmea_val:
            return None
            
        dot_index = nmea_val.find('.')
        if dot_index == -1:
            return None # 不正なフォーマット

        deg_chars_index = dot_index - 2
        
        degrees = float(nmea_val[:deg_chars_index])
        minutes = float(nmea_val[deg_chars_index:])
            
        decimal_degrees = degrees + (minutes / 60)
        
        if direction in ('S', 'W'):
            decimal_degrees = -decimal_degrees
            
        return decimal_degrees
    except ValueError:
        return None # 変換エラー

def parse_nmea_time(time_str):
    """
    NMEAの時刻文字列 (HHMMSS.sss) を datetime.time オブジェクトに変換
    """
    if not time_str or '.' not in time_str:
        return None
    try:
        h = int(time_str[0:2])
        m = int(time_str[2:4])
        s_full = float(time_str[4:])
        s = int(s_full)
        ms = int((s_full - s) * 1_000_000) # マイクロ秒
        
        # タイムゾーン情報を付加 (UTC)
        return datetime.time(hour=h, minute=m, second=s, microsecond=ms, tzinfo=datetime.timezone.utc)
    except Exception:
        return None

def calculate_distance_km(lat1, lon1, lat2, lon2):
    """
    2点間の緯度経度から距離(km)を計算する (ハヴァサイン公式)
    """
    # 地球の半径 (km)
    R = 6371.0 
    
    # (0, 0) または無効な座標の場合は 0 を返す
    if (lat1 == 0.0 and lon1 == 0.0) or (lat2 == 0.0 and lon2 == 0.0):
        return 0.0
        
    # 緯度経度をラジアンに変換
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 差分
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    # ハヴァサイン公式
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def calculate_distance_meters(lat1, lon1, lat2, lon2):
    """
    2点間の緯度経度から距離(m)を計算する
    """
    return calculate_distance_km(lat1, lon1, lat2, lon2) * 1000.0


# ===============================================
# GPS Worker クラス
# ===============================================

class GpsWorker(QObject):
    data_received = pyqtSignal(dict) # 処理されたGPSデータ
    error_occurred = pyqtSignal(str) # エラーメッセージ

    def __init__(self, port, baudrate, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self._running = True
        self.ser = None
        
        # 走行距離と前回の座標
        self.total_distance_km = 0.0
        self.last_valid_latitude = 0.0
        self.last_valid_longitude = 0.0
        
        # データを一時保存する
        self.last_known_data = {
            "time": None,       # datetime.time オブジェクト
            "latitude": 0.0,
            "longitude": 0.0,
            "quality": 0,       # GGA の測位品質
            "sats": 0,          # GGA の衛星数
            "status": 'V',      # RMC のステータス (A=Active, V=Void)
            "speed_kph": 0.0,   # VTG の速度 (km/h)
            "total_distance_km": 0.0
        }

    def stop(self):
        """スレッドとシリアルポートを停止する"""
        self._running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception as e:
                print(f"シリアルポートクローズエラー: {e}")

    def run(self):
        """シリアルポートからNMEAデータを読み込み、手動で解析し、距離を計算する"""
        try:
            # シリアルポートを開く
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1.0) 
            print(f"GPS: シリアルポート {self.port} を開きました。受信待機中...")
            
            raw_line_count = 0
            
            while self._running:
                if not self.ser.is_open:
                    break
                
                line = None
                try:
                    # 1行読み込み
                    line = self.ser.readline().decode('ascii', errors='ignore').strip()
                    
                    if not line:
                        continue
                    
                    # 最初の数行はデバッグ用に表示
                    if raw_line_count < 5:
                        print(f"GPS Raw Data: {line}")
                        raw_line_count += 1

                    # $GNGGA, $GNRMC, $GNVTG などを解析
                    if line.startswith(("$GN", "$GP")):
                        
                        # NMEAセンテンスを1行パースし、データが更新されたか確認
                        updated_data = self.parse_nmea_line(line)
                        
                        if updated_data:
                            # データが更新された場合、距離計算などを行う
                            
                            # 現在の有効な座標と品質を取得
                            current_lat = self.last_known_data.get("latitude", 0.0)
                            current_lon = self.last_known_data.get("longitude", 0.0)
                            quality = self.last_known_data.get("quality", 0)
                            status = self.last_known_data.get("status", 'V')
                            
                            # (0,0) でない、かつ品質が有効な場合
                            is_valid_fix = (quality > 0 or status == 'A') and (current_lat != 0.0 or current_lon != 0.0)

                            # 距離計算のロジック
                            if is_valid_fix:
                                # 測位が有効な場合
                                if self.last_valid_latitude != 0.0 or self.last_valid_longitude != 0.0:
                                    # 前回の有効な座標がある場合のみ距離を計算
                                    distance_diff = calculate_distance_km(
                                        self.last_valid_latitude, self.last_valid_longitude,
                                        current_lat, current_lon
                                    )
                                    
                                    # 極端に大きな移動（瞬間移動）は無視する
                                    # 1秒（timeout=1.0）で 500m (1800km/h) 以上の移動は異常値とする
                                    if distance_diff < 0.5: 
                                        self.total_distance_km += distance_diff
                                        
                                # 今回の有効な座標を保存
                                self.last_valid_latitude = current_lat
                                self.last_valid_longitude = current_lon
                            
                            # 走行距離を送信データに含める
                            self.last_known_data["total_distance_km"] = self.total_distance_km
                            
                            # シグナルを送信 (コピーを渡すことで参照によるバグを防ぐ)
                            self.data_received.emit(self.last_known_data.copy())
                            
                except serial.SerialException as se:
                    if self._running:
                        self.error_occurred.emit(f"GPSシリアルエラー: {se}")
                    break # ループ終了
                except Exception as e:
                    # パース中の一般的なエラー
                    pass 

        except serial.SerialException as e:
            if self._running:
                self.error_occurred.emit(f"シリアルポート '{self.port}' が開けません: {e}")
        except Exception as e:
            if self._running:
                self.error_occurred.emit(f"予期せぬ実行エラー (GPS): {e}")
        finally:
            self.stop() 
            print("GPSWorker 終了")

    def parse_nmea_line(self, line):
        """
        NMEAセンテンスを1行パースし、last_known_dataを更新する
        戻り値: データが更新された場合は True
        """
        try:
            if '$' not in line:
                return False 
                
            sentence_part = line[line.find('$'):]
            parts = sentence_part.split('*')[0].split(',')
            sentence_type = parts[0]
            
            # $GNGGA,時刻,緯度,N/S,経度,E/W,測位品質,衛星数,...
            if sentence_type.endswith('GGA'): 
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
                        self.last_known_data["latitude"] = nmea_to_decimal_degrees(lat_str, lat_dir)
                        self.last_known_data["longitude"] = nmea_to_decimal_degrees(lon_str, lon_dir)
                    
                    self.last_known_data["quality"] = int(q_str) if q_str else 0
                    self.last_known_data["sats"] = int(sats_str) if sats_str else 0

                    if self.last_known_data["quality"] > 0:
                        self.last_known_data["status"] = 'A'
                    else:
                        self.last_known_data["status"] = 'V'
                        
                    return True # データ更新

            # $GNRMC,時刻,ステータス,緯度,N/S,経度,E/W,速度(knot),...
            elif sentence_type.endswith('RMC'):
                if len(parts) > 6:
                    time_str = parts[1]
                    status_str = parts[2] # 'A' or 'V'
                    lat_str = parts[3]
                    lat_dir = parts[4]
                    lon_str = parts[5]
                    lon_dir = parts[6]

                    self.last_known_data["time"] = parse_nmea_time(time_str)
                    self.last_known_data["status"] = status_str
                    
                    if lat_str and lon_str:
                        self.last_known_data["latitude"] = nmea_to_decimal_degrees(lat_str, lat_dir)
                        self.last_known_data["longitude"] = nmea_to_decimal_degrees(lon_str, lon_dir)

                    if status_str == 'A' and self.last_known_data["quality"] == 0:
                        self.last_known_data["quality"] = 1 # RMCが有効なら、最低品質1
                    elif status_str == 'V':
                        self.last_known_data["quality"] = 0

                    return True # データ更新

            # $GNVTG,......,速度(km/h),K*cs
            elif sentence_type.endswith('VTG'): 
                if len(parts) > 8:
                    speed_str = parts[7] # 速度(km/h)
                    self.last_known_data["speed_kph"] = float(speed_str) if speed_str else 0.0
                    return True # データ更新
                    
        except Exception as e:
            # パースエラーは無視して次のデータへ
            pass
            
        return False # データ更新なし