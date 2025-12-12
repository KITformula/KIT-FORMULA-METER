import time
import zlib
from dataclasses import dataclass
from typing import List

import can
from src.fuel.fuel_calculator import FuelCalculator
from src.models.models import (
    BatteryVoltage,
    DashMachineInfo,
    FuelPress,
    GearVoltage,
    OilTemp,
    WaterTemp,
)
from src.util import config


@dataclass
class CanIdLength:
    id: int
    length: int


class DashInfoListener(can.Listener):
    CAN_ID = 0xE8
    PACKET_SIZE = 176
    HEADER = bytes([0x82, 0x81, 0x80])

    def __init__(self, fuel_calculator: FuelCalculator) -> None:
        super().__init__()
        self.buffer = bytearray()
        self.dashMachineInfo = DashMachineInfo()
        self.last_packet_timestamp: float | None = None
        self.fuel_calculator = fuel_calculator

    def on_message_received(self, msg: can.Message) -> None:
        if msg.arbitration_id != self.CAN_ID:
            return

        if msg.data.startswith(self.HEADER):
            self.buffer = bytearray(msg.data)
            return

        if 0 < len(self.buffer) < self.PACKET_SIZE:
            self.buffer.extend(msg.data)

        if len(self.buffer) >= self.PACKET_SIZE:
            self._process_full_packet()
            self.buffer.clear()

    def _process_full_packet(self) -> None:
        data_to_check = self.buffer[:172]
        received_crc = int.from_bytes(self.buffer[172:176], "big")
        calculated_crc = zlib.crc32(data_to_check)

        if calculated_crc != received_crc:
            return

        current_time = time.time()
        delta_t = 0.0
        if self.last_packet_timestamp is not None:
            delta_t = current_time - self.last_packet_timestamp

        self.last_packet_timestamp = current_time
        self.dashMachineInfo.delta_t = delta_t

        try:
            rpm_val = int.from_bytes(self.buffer[4:6], "big")
            self.dashMachineInfo.setRpm(rpm_val)

            tp_val = round(int.from_bytes(self.buffer[6:8], "big") * 0.1, 1)
            self.dashMachineInfo.throttlePosition = tp_val

            wt_val = round(int.from_bytes(self.buffer[12:14], "big") * 0.1, 1)
            self.dashMachineInfo.waterTemp = WaterTemp(int(wt_val))

            ot_val = round(int.from_bytes(self.buffer[26:28], "big") * 0.1, 1)
            self.dashMachineInfo.oilTemp = OilTemp(int(ot_val))

            op_val = round(int.from_bytes(self.buffer[28:30], "big") * 0.1, 1)
            self.dashMachineInfo.oilPress.oilPress = op_val

            gv_val = round(int.from_bytes(self.buffer[30:32], "big") * 0.01, 2)
            self.dashMachineInfo.gearVoltage = GearVoltage(gv_val)

            bv_val = round(int.from_bytes(self.buffer[48:50], "big") * 0.01, 2)
            self.dashMachineInfo.batteryVoltage = BatteryVoltage(bv_val)

            fp_val = round(int.from_bytes(self.buffer[24:26], "big") * 0.1, 1)
            self.dashMachineInfo.fuelPress = FuelPress(int(fp_val))

            # --- ★変更: Fuel Used (Bytes 92:93) ---
            # 単位は「Litres (リットル)」。
            # FuelCalculatorは ml (ミリリットル) で管理するため、
            # config.FUEL_USED_SCALING (デフォルト 1000.0) を掛けて ml に変換する。
            raw_fuel_used_liters = int.from_bytes(self.buffer[92:94], "big")
            
            # ml に変換
            fuel_used_ml = raw_fuel_used_liters * config.FUEL_USED_SCALING
            
            self.dashMachineInfo.fuelUsed = fuel_used_ml

            # FuelCalculator に ml 単位の値を渡す
            self.fuel_calculator.update_from_ecu(fuel_used_ml)

        except IndexError:
            print("MoTeC Protocol: Packet parsing error due to invalid length!")


class UdpPayloadListener(can.Listener):
    MOTEC_CAN_ID_LENGTHS = [
        CanIdLength(0x5F0, 8),
        CanIdLength(0x5F1, 8),
        CanIdLength(0x5F2, 8),
        CanIdLength(0x5F3, 8),
        CanIdLength(0x5F4, 6),
    ]

    DATA_LOGGER_CAN_ID_LENGTHS = [
        CanIdLength(0x700, 8),
        CanIdLength(0x701, 8),
        CanIdLength(0x702, 8),
        CanIdLength(0x703, 8),
        CanIdLength(0x704, 8),
        CanIdLength(0x705, 8),
        CanIdLength(0x706, 8),
        CanIdLength(0x707, 8),
        CanIdLength(0x708, 8),
        CanIdLength(0x709, 8),
        CanIdLength(0x70A, 8),
        CanIdLength(0x70B, 8),
        CanIdLength(0x70C, 8),
        CanIdLength(0x70D, 8),
        CanIdLength(0x70E, 8),
    ]

    canIdLength: List[CanIdLength]
    receivedMessages: dict[int, can.Message]

    def __init__(self) -> None:
        self.canIdLength = sorted(
            self.MOTEC_CAN_ID_LENGTHS + self.DATA_LOGGER_CAN_ID_LENGTHS,
            key=lambda il: il.id,
        )
        self.receivedMessages = {}
        super().__init__()

    def on_message_received(self, msg: can.Message) -> None:
        self.receivedMessages[msg.arbitration_id] = msg

    def getUdpPayload(self, machineId: int, runId: int, errorCode: int) -> bytes:
        bs = bytearray()
        bs += (machineId & 0xFFFFFFFF).to_bytes(4, "little")
        bs += (runId & 0xFFFFFFFF).to_bytes(4, "little")
        bs += (errorCode & 0xFF).to_bytes(1, "little")
        bs += (int(time.time() * 1000) & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little")
        for il in self.canIdLength:
            startIndex = len(bs)
            bs += bytes(il.length)
            if il.id in self.receivedMessages:
                for i in range(min(il.length, self.receivedMessages[il.id].dlc)):
                    bs[startIndex + i] = self.receivedMessages[il.id].data[i]
        return bytes(bs)