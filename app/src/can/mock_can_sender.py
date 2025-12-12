import threading
import time
import zlib
from typing import List

import can


class MockMachine:
    """
    MoTeC Set 3 プロトコルに基づいて、擬似的な車両データを保持・生成するクラス。
    """

    def __init__(self):
        self.rpm: int = 0
        self.throttlePosition: float = 0.0
        self.manifoldPressure: float = 101.3
        self.engineTemperature: float = 90.0
        self.oilTemperature: float = 100.0
        self.oilPressure: float = 4.5
        self.gearVoltage: float = 2.5
        self.batteryVoltage: float = 13.8
        self.fuelPressure: float = 30.0
        
        # ★変更: FuelUsed (Litres)
        # 16bit intなので、0, 1, 2... とリットル単位で増える
        self.fuelUsedLitres: int = 0

    def to_motec_set3_messages(self) -> List[can.Message]:
        packet = bytearray(176)

        # Header
        packet[0:3] = [0x82, 0x81, 0x80]
        packet[3] = 84

        try:
            packet[4:6] = (self.rpm & 0xFFFF).to_bytes(2, "big")
            packet[6:8] = (round(self.throttlePosition * 10) & 0xFFFF).to_bytes(2, "big")
            packet[8:10] = (round(self.manifoldPressure * 10) & 0xFFFF).to_bytes(2, "big")
            packet[12:14] = (round(self.engineTemperature * 10) & 0xFFFF).to_bytes(2, "big")
            packet[24:26] = (round(self.fuelPressure * 10) & 0xFFFF).to_bytes(2, "big")
            packet[26:28] = (round(self.oilTemperature * 10) & 0xFFFF).to_bytes(2, "big")
            packet[28:30] = (round(self.oilPressure * 10) & 0xFFFF).to_bytes(2, "big")
            packet[30:32] = (round(self.gearVoltage * 100) & 0xFFFF).to_bytes(2, "big")
            packet[48:50] = (round(self.batteryVoltage * 100) & 0xFFFF).to_bytes(2, "big")

            # ★変更: Byte 92:93 Fuel Used (Litres)
            # 16bit int (0-65535 Litres)
            packet[92:94] = (self.fuelUsedLitres & 0xFFFF).to_bytes(2, "big")

        except Exception as e:
            print(f"Error packing data: {e}")
            return []

        data_to_check = packet[:172]
        calculated_crc = zlib.crc32(data_to_check)
        packet[172:176] = calculated_crc.to_bytes(4, "big")

        messages = []
        for i in range(22):
            start = i * 8
            end = start + 8
            data_chunk = packet[start:end]
            msg = can.Message(
                arbitration_id=0xE8,
                is_extended_id=False,
                data=data_chunk,
            )
            messages.append(msg)

        return messages


class MockCanSender:
    def __init__(self) -> None:
        self.bus = can.Bus(channel="debug", interface="virtual")
        self.machine = MockMachine()

    def __del__(self) -> None:
        self.bus.shutdown()

    def updateMachine(self):
        t = int(time.time() * 1000)
        self.machine.rpm = 2500 + (t % 12000)
        self.machine.throttlePosition = (t % 1001) / 10.0
        self.machine.engineTemperature = 50 + (t % 400) / 10.0
        self.machine.oilTemperature = 90 + (t % 400) / 10.0
        self.machine.oilPressure = 30.0 + (t % 70) / 0.1
        self.machine.gearVoltage = 0.5 + (t % 4501) / 1000.0
        self.machine.batteryVoltage = 9.0 + (t % 500) / 10.0
        self.machine.fuelPressure = 27.0 + (t % 100) / 10.0
        
        # ★追加: 燃料使用量 (リットル) のシミュレーション
        # 1リットル消費するのに時間がかかるため、非常にゆっくり増やす
        # 例: 10秒(10000ms)ごとに1リットル増える (かなり早いがテスト用)
        self.machine.fuelUsedLitres = int((t / 10000) % 65000)

    def sendEvery(self):
        while True:
            self.updateMachine()
            messages_to_send = self.machine.to_motec_set3_messages()

            for msg in messages_to_send:
                self.bus.send(msg)
                time.sleep(0.0005)

            time.sleep(0.05)

    def start(self):
        t = threading.Thread(target=self.sendEvery)
        t.setDaemon(True)
        t.start()