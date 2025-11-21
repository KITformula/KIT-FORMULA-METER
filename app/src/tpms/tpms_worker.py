import json
import random  # ★ 2. モックのランダムデータ用にインポート
import subprocess
import threading
import time  # ★ 1. モックの待機用にインポート

from PyQt5.QtCore import QObject, pyqtSignal

# (config は Application から渡されるため不要)


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

        command = ["rtl_433", "-F", "json", "-f", self.frequency]

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

                data = json.loads(line.strip())

                if "id" in data and str(data["id"]) in self.id_map:
                    self._parse_and_emit(data)

            except json.JSONDecodeError:
                pass
            except Exception as e:
                if self.is_running:
                    print(f"TPMSワーカーエラー: {e}")

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
                mock_data = {}
                for key, name in self.id_map.items():  # "FL", "FR" ...
                    mock_data[name] = {
                        "temp_c": round(20.0 + random.uniform(-2.0, 2.0), 1),
                        "pressure_kpa": round(220.0 + random.uniform(-5.0, 5.0), 0),
                    }

                # データをまとめてシグナルで送信
                # (注: _parse_and_emit 形式ではなく、Applicationが期待する形式に合わせる)
                # self.data_updated.emit(mock_data) # ← これだと4つまとめて送ってしまう

                # 1つずつ送る (よりリアルなシミュレーション)
                for position, data in mock_data.items():
                    self.data_updated.emit({position: data})
                    time.sleep(0.1)  # わずかに時間をずらす

                print(f"MOCK TPMSデータ送信: {mock_data['FL']}")  # ログにはFLだけ表示

                # 2秒待機
                time.sleep(2.0)

            except Exception as e:
                if self.is_running:
                    print(f"TPMSモックワーカーエラー: {e}")

        print("TPMSワーカー(モック)が停止しました。")

    def _parse_and_emit(self, data: dict):
        """(本番用) JSONを解析してシグナルを発行"""
        try:
            sensor_id_str = str(data["id"])
            tire_position = self.id_map[sensor_id_str]

            temp_c = data.get("temperature_C")
            pressure_kpa = data.get("pressure_kPa")

            if temp_c is not None and pressure_kpa is not None:
                update_data = {
                    tire_position: {"temp_c": temp_c, "pressure_kpa": pressure_kpa}
                }
                self.data_updated.emit(update_data)

        except KeyError as e:
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
