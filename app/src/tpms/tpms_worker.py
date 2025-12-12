import json
import random  # ★ 2. モックのランダムデータ用にインポート
import subprocess
import threading
import time  # ★ 1. モックの待機用にインポート

from PyQt5.QtCore import QObject, pyqtSignal

# ===============================================
# TPMS 補正関数
# ===============================================

# 圧力補正関数: x = (y + 0.6896) / 0.4221
def get_correct_pressure_kpa(wrong_kpa_from_rtl433: float) -> float:
    """
    rtl_433が出力した誤認識値(y)から、正しい圧力(x)を計算し、
    結果を最も近い10 kPaの倍数に丸める。
    """
    y = wrong_kpa_from_rtl433
    # 0除算を避けるための安全チェック
    if abs(0.4221) < 1e-6:
        return 0.0
    
    # 1. 補正計算
    x = (y + 0.6896) / 0.4221
    
    # 2. 最も近い10 kPaの倍数に丸める (10 kPa単位のセンサー出力に合わせる)
    rounded_x = round(x / 10) * 10
    
    return rounded_x

# 温度補正関数: 取得値から 5 を引く
def correct_temperature(temperature_from_rtl433: float) -> float:
    """rtl_433が出力した温度に -5 の補正を適用する"""
    return temperature_from_rtl433 - 5

# ===============================================
# TPMS Worker クラス
# ===============================================


class TpmsWorker(QObject):
    data_updated = pyqtSignal(dict)

    # ★ 3. __init__ を修正 (debug_mode を受け取る)
    def __init__(self, frequency: str, id_map: dict, debug_mode: bool = False):
        super().__init__()
        self.frequency = frequency
        self.id_map = id_map
        self.debug_mode = debug_mode  # ★ デバッグモードを保持
        self.process = None
        self.thread = None
        self.is_running = False

    def _run(self):
        """(内部メソッド) 「本番用」スレッド (rtl_433 を実行)"""

        # 周波数とゲイン '37' を追加
        command = ["rtl_433", "-f", self.frequency, "-g", "37", "-F", "json"]

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
        except FileNotFoundError:
            print("エラー: rtl_433 コマンドが見つかりません。")
            self.is_running = False
            return

        print(f"TPMSワーカー開始 (本番モード): {command}")

        while self.is_running and self.process.stdout:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break

                # JSONではない出力（起動メッセージなど）は無視
                if line.strip().startswith('{'):
                    data = json.loads(line.strip())

                    # 'id' の存在とマッピングをチェック
                    if data.get("model") == 'Abarth-124Spider' and str(data.get("id")) in self.id_map:
                        self._parse_and_emit(data)

            except json.JSONDecodeError:
                pass
            except Exception as e:
                if self.is_running:
                    print(f"TPMSワーカーエラー (実行中): {e}")

        if self.is_running:
            print("TPMSワーカー(本番)が停止しました。")
            self.is_running = False
            
    # ★ 4. 「モック用」のスレッドを新設
    def _run_mock(self):
        """(内部メソッド) 「デバッグ用」スレッド (偽のデータを送信)"""
        print("TPMSワーカー開始 (モックモード): 2秒ごとに偽のデータを送信します。")

        while self.is_running:
            try:
                # 4つのタイヤのモックデータを作成
                for sensor_id, position in self.id_map.items():
                    
                    # 補正前の 'rtl_433っぽい' 生データを作成
                    # Pressure (例: 200kPa前後, 10kPa単位丸め前の値)
                    raw_pressure = round(200.0 + random.uniform(-10.0, 10.0), 1)
                    # Temperature (例: 25C前後)
                    raw_temperature = round(25.0 + random.uniform(-5.0, 5.0), 1)
                    
                    # ★ 補正計算の実行 (モックデータにも適用) ★
                    correct_pressure = get_correct_pressure_kpa(raw_pressure)
                    corrected_temperature = correct_temperature(raw_temperature)

                    # 1つずつ送る (よりリアルなシミュレーション)
                    # Application側が期待する形式: { position: { temp_c: X, pressure_kpa: Y } }
                    payload_for_main_window = {
                        position: {
                            "temp_c": corrected_temperature, 
                            "pressure_kpa": correct_pressure
                        }
                    }
                    self.data_updated.emit(payload_for_main_window)
                    time.sleep(0.1)  # わずかに時間をずらす

                # ログにはFLだけ表示
                print(f"MOCK TPMSデータ送信: {self.id_map['64f3850c']}: {correct_pressure:.0f} kPa / {corrected_temperature:.0f} °C") 

                # 2秒待機
                time.sleep(2.0)

            except Exception as e:
                if self.is_running:
                    print(f"TPMSモックワーカーエラー: {e}")

        print("TPMSワーカー(モック)が停止しました。")

    def _parse_and_emit(self, data: dict):
        """(本番用) JSONを解析し、補正を適用してシグナルを発行"""
        try:
            sensor_id_str = str(data["id"])
            
            # マッピングに存在しないIDはここでKeyErrorが発生する
            tire_position = self.id_map[sensor_id_str]

            temp_raw = data.get("temperature_C") # raw の温度
            pressure_raw = data.get("pressure_kPa") # raw の圧力

            if temp_raw is not None and pressure_raw is not None:
                
                # ★ 圧力と温度の補正計算を実行 ★
                correct_pressure = get_correct_pressure_kpa(pressure_raw)
                corrected_temperature = correct_temperature(temp_raw)
                
                # シグナルで送信するデータ構造を構築 (補正済みの値を使用)
                # 形式: { position: { temp_c: X, pressure_kpa: Y } }
                update_data = {
                    tire_position: {
                        "temp_c": corrected_temperature, 
                        "pressure_kpa": correct_pressure
                    }
                }
                self.data_updated.emit(update_data)

        except KeyError:
            # マッピング辞書に存在しないIDを受信した場合
            pass
        except Exception as e:
            print(f"TPMSデータの解析に失敗: {e} - JSON: {data}")

    # ★ 5. start() を修正 (デバッグモードで分岐)
    def start(self):
        """ワーカーを別スレッドで起動する"""
        if not self.is_running:
            self.is_running = True

            if self.debug_mode:
                # デバッグモードなら、モック用スレッドを開始
                self.thread = threading.Thread(target=self._run_mock)
            else:
                # 本番モードなら、本物(rtl_433)スレッドを開始
                self.thread = threading.Thread(target=self._run)

            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        """ワーカーとサブプロセスを停止する"""
        print("TPMSワーカーを停止しています...")
        self.is_running = False

        if self.process:
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass

        if self.thread:
            self.thread.join(timeout=1.0)