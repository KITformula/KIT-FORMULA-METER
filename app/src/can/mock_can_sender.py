import threading
import time
import can
import zlib
from typing import List

class MockMachine:
    """
    MoTeC Set 3 プロトコルに基づいて、擬似的な車両データを保持・生成するクラス。
    """
    def __init__(self):
        # PDFに記載されている各パラメータを初期化
        self.rpm: int = 0
        self.throttlePosition: float = 0.0
        self.manifoldPressure: float = 101.3
        self.engineTemperature: float = 90.0
        self.oilTemperature: float = 100.0
        self.oilPressure: float = 4.5
        self.gearVoltage: float = 2.5
        self.batteryVoltage: float = 13.8
        self.fuelPressure: float = 3.0
        self.fuelEffectivePulseWidth: float = 0.0

    def to_motec_set3_messages(self) -> List[can.Message]:
        """
        現在のマシン状態から、176バイトのデータパケットを構築し、
        22個の8バイトCANフレームに分割して返す。
        """
        # 1. 176バイトの空のバイト配列を用意
        packet = bytearray(176)

        # 2. ヘッダーとデータ長を設定 (PDF参照)
        packet[0:3] = [0x82, 0x81, 0x80]
        packet[3] = 84 

        # 3. 各パラメータをスケール変換し、ビッグエンディアンの2バイトで書き込む (PDF参照)
        try:
            packet[4:6]   = (self.rpm & 0xFFFF).to_bytes(2, "big")
            packet[6:8]   = (round(self.throttlePosition * 10) & 0xFFFF).to_bytes(2, "big")
            packet[8:10]  = (round(self.manifoldPressure * 10) & 0xFFFF).to_bytes(2, "big")
            packet[12:14] = (round(self.engineTemperature * 10) & 0xFFFF).to_bytes(2, "big")
            packet[24:26] = (round(self.fuelPressure * 10) & 0xFFFF).to_bytes(2, "big")
            packet[26:28] = (round(self.oilTemperature * 10) & 0xFFFF).to_bytes(2, "big")
            packet[28:30] = (round(self.oilPressure * 10) & 0xFFFF).to_bytes(2, "big")
            packet[30:32] = (round(self.gearVoltage * 100) & 0xFFFF).to_bytes(2, "big")
            packet[48:50] = (round(self.batteryVoltage * 100) & 0xFFFF).to_bytes(2, "big")
            
            # 仕様書通り、0.5 µs単位なので、実際の値を0.5で割る (つまり2を掛ける)
            fepw_val = round(self.fuelEffectivePulseWidth * 2)
            packet[112:114] = (fepw_val & 0xFFFF).to_bytes(2, "big")
            
        except Exception as e:
            print(f"Error packing data: {e}")
            return []

        # 4. CRC32を計算 (ヘッダーとデータ部、合計172バイトが対象)
        data_to_check = packet[:172]
        calculated_crc = zlib.crc32(data_to_check)

        # 計算したCRCをパケットの末尾4バイトに書き込む
        packet[172:176] = calculated_crc.to_bytes(4, "big")

        # 5. 176バイトのパケットを、22個の8バイトCANフレームに分割
        messages = []
        for i in range(22):
            start = i * 8
            end = start + 8
            data_chunk = packet[start:end]
            msg = can.Message(
                arbitration_id=0xE8, # 10進数で232
                is_extended_id=False,
                data=data_chunk
            )
            messages.append(msg)
            
        return messages


class MockCanSender:
    """
    MockMachineの状態を定期的に更新し、
    MoTeC Set 3 プロトコルに従ったCANメッセージを仮想バスに送信するクラス。
    """
    def __init__(self) -> None:
        self.bus = can.Bus(channel="debug", interface="virtual")
        self.machine = MockMachine()

    def __del__(self) -> None:
        self.bus.shutdown()

    def updateMachine(self):
        """時間に応じてマシンのパラメータを擬似的に変動させる。"""
        # ミリ秒単位の整数時間をベースに計算することで、浮動小数点数の誤差を減らす
        t = int(time.time() * 1000)
        self.machine.rpm = 1000 + (t % 8000)
        self.machine.throttlePosition = (t % 1001) / 10.0 # 1001にすることで0.0も表現
        self.machine.engineTemperature = 80 + (t % 400) / 10.0
        self.machine.oilTemperature = 90 + (t % 400) / 10.0
        self.machine.oilPressure = 1.0 + (t % 70) / 10.0
        self.machine.gearVoltage = 0.5 + (t % 4501) / 1000.0
        self.machine.batteryVoltage = 12.0 + (t % 251) / 100.0
        self.machine.fuelPressure = 3.0 + (t % 11) / 10.0
        self.machine.fuelEffectivePulseWidth = 800 + (t % 9200)

    def sendEvery(self):
        """無限ループで、一定間隔ごとにCANメッセージを送信する。"""
        while True:
            self.updateMachine()
            messages_to_send = self.machine.to_motec_set3_messages()
            
            for msg in messages_to_send:
                self.bus.send(msg)
                time.sleep(0.0005) 
            
            time.sleep(0.05)

    def start(self):
        """バックグラウンドスレッドで送信ループを開始する。"""
        t = threading.Thread(target=self.sendEvery)
        t.setDaemon(True)
        t.start()

