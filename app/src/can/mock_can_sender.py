import threading
import time
import zlib
from typing import List

import can
from src.util import config  # 係数取得のためにimport

class MockMachine:
    """
    MoTeC Set 3 プロトコルに基づいて、擬似的な車両データを保持・生成するクラス。
    """

    def __init__(self):
        self.rpm: int = 0
        self.throttlePosition: float = 0.0
        self.manifoldPressure: float = 101.3
        self.engineTemperature: float = 90.0
        self.lambda1: float = 1.000
        self.oilTemperature: float = 100.0
        self.oilPressure: float = 4.5
        self.gearVoltage: float = 2.5
        self.batteryVoltage: float = 13.8
        self.fuelPressure: float = 30.0
        
        # 16bitのRaw値 (ECUが送ってくる値をシミュレート)
        self.fuelUsedRaw: int = 0

    def to_motec_set3_messages(self) -> List[can.Message]:
        packet = bytearray(176)

        # Header
        packet[0:3] = [0x82, 0x81, 0x80]
        packet[3] = 84

        try:
            packet[4:6] = (self.rpm & 0xFFFF).to_bytes(2, "big")
            packet[6:8] = (round(self.throttlePosition * 10) & 0xFFFF).to_bytes(2, "big")
            
            # Manifold Pressure (0.1 kPa)
            packet[8:10] = (round(self.manifoldPressure * 10) & 0xFFFF).to_bytes(2, "big")
            
            packet[12:14] = (round(self.engineTemperature * 10) & 0xFFFF).to_bytes(2, "big")
            
            # Lambda 1 (0.001 La)
            packet[14:16] = (round(self.lambda1 * 1000) & 0xFFFF).to_bytes(2, "big")
            
            packet[24:26] = (round(self.fuelPressure * 10) & 0xFFFF).to_bytes(2, "big")
            packet[26:28] = (round(self.oilTemperature * 10) & 0xFFFF).to_bytes(2, "big")
            packet[28:30] = (round(self.oilPressure * 10) & 0xFFFF).to_bytes(2, "big")
            packet[30:32] = (round(self.gearVoltage * 100) & 0xFFFF).to_bytes(2, "big")
            packet[48:50] = (round(self.batteryVoltage * 100) & 0xFFFF).to_bytes(2, "big")

            # Fuel Used (Bytes 92:93)
            # 16bit int (0-65535)
            packet[92:94] = (self.fuelUsedRaw & 0xFFFF).to_bytes(2, "big")

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
        
        # 内部計算用の積算燃料 (mL)
        self.simulated_total_fuel_ml = 0.0
        
        # タイムステップ計算用
        self.last_update_time = time.time()

    def __del__(self) -> None:
        self.bus.shutdown()

    def updateMachine(self):
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now
        
        # 時間ベースの変動 (既存ロジック)
        t_ms = int(now * 1000)
        
        # RPM: 2500〜14500 の間で変動
        self.machine.rpm = 2500 + (t_ms % 12000)
        
        # TPS: 0〜100% の間で変動
        self.machine.throttlePosition = (t_ms % 1001) / 10.0
        
        # その他のパラメータ
        self.machine.engineTemperature = 50 + (t_ms % 400) / 10.0
        self.machine.oilTemperature = 90 + (t_ms % 400) / 10.0
        self.machine.oilPressure = 30.0 + (t_ms % 70) / 0.1
        self.machine.gearVoltage = 0.5 + (t_ms % 4501) / 1000.0
        self.machine.batteryVoltage = 12.0 + (t_ms % 200) / 100.0
        self.machine.fuelPressure = 300.0 + (t_ms % 200) / 10.0
        self.machine.manifoldPressure = 100.0 + (t_ms % 5000) / 50.0 
        self.machine.lambda1 = 0.8 + (t_ms % 4000) / 10000.0
        
        # ★ 燃料消費シミュレーション
        # 基本消費量 + RPM依存 + スロットル依存 (mL/sec)
        # 例: アイドリング0.5ml/s, 全開で最大10ml/sくらいと仮定
        rpm_factor = (self.machine.rpm / 15000.0) * 8.0
        tps_factor = (self.machine.throttlePosition / 100.0) * 2.0
        base_flow = 0.2
        
        current_flow_ml_sec = base_flow + rpm_factor + tps_factor
        
        # 今回のステップ(dt秒)で消費した量を加算
        consumed_this_step = current_flow_ml_sec * dt
        self.simulated_total_fuel_ml += consumed_this_step
        
        # ECUのRaw値に変換 (逆算: mL / SCALING)
        # SCALING = 0.1666... なので、Raw = mL * 6 くらい
        if config.FUEL_USED_SCALING > 0:
            raw_value = int(self.simulated_total_fuel_ml / config.FUEL_USED_SCALING)
        else:
            raw_value = int(self.simulated_total_fuel_ml)

        # 16bit (65535) でループさせる (実車ECUの挙動を模倣)
        self.machine.fuelUsedRaw = raw_value % 65536

    def sendEvery(self):
        while True:
            self.updateMachine()
            messages_to_send = self.machine.to_motec_set3_messages()

            for msg in messages_to_send:
                self.bus.send(msg)
                time.sleep(0.0005)

            # 更新頻度 (20Hz)
            time.sleep(0.05)

    def start(self):
        t = threading.Thread(target=self.sendEvery)
        t.setDaemon(True)
        t.start()