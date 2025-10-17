import time
from dataclasses import dataclass
from typing import List

import can

import zlib

from src.models.models import (
    BatteryVoltage,
    DashMachineInfo,
    FuelPress,
    GearVoltage,
    OilTemp,
    WaterTemp,
)


@dataclass
class CanIdLength:
    id: int
    length: int


class DashInfoListener(can.Listener):
    """
    MoTeC Set 3 データプロトコル（複数フレーム）を組み立て、
    解析して dashMachineInfo オブジェクトを更新するステートフルなリスナー。
    """
    CAN_ID = 0xE8  # MoTeC Set 3 protocol CAN ID
    PACKET_SIZE = 176
    HEADER = bytes([0x82, 0x81, 0x80])

    def __init__(self) -> None:
        super().__init__()
        # 複数のCANフレームを結合するためのバッファ
        self.buffer = bytearray()
        # 解析済みの最新データを保持するためのオブジェクト
        self.dashMachineInfo = DashMachineInfo()

    def on_message_received(self, msg: can.Message) -> None:
        """NotifierからCANメッセージが届くたびに呼び出される。"""
        
        # 1. 目的のCAN ID (0xE8) かどうかをチェック
        if msg.arbitration_id != self.CAN_ID:
            return # 関係ないIDのメッセージは無視

        # 2. パケットの先頭かどうかをチェック
        if msg.data.startswith(self.HEADER):
            # 新しいパケットの始まりなので、バッファをリセット
            self.buffer = bytearray(msg.data)
            return

        # 3. パケットの組み立て途中であれば、データをバッファに追加
        if 0 < len(self.buffer) < self.PACKET_SIZE:
            self.buffer.extend(msg.data)

        # 4. パケットが完全に揃ったかチェック
        if len(self.buffer) >= self.PACKET_SIZE:
            # CRCチェックとデータの解析を行う
            self._process_full_packet()
            # 処理が終わったら、次のパケットのためにバッファをクリア
            self.buffer.clear()

    def _process_full_packet(self) -> None:
        """
        組み立てが完了した176バイトの完全なパケットを処理
        """
        # 5. CRCチェック
        data_to_check = self.buffer[:172]
        received_crc = int.from_bytes(self.buffer[172:176], 'big')
        calculated_crc = zlib.crc32(data_to_check)

        if calculated_crc != received_crc:
            # CRCが一致しないデータは不正とみなし、処理を中断
            return

        # 6. CRCが一致した場合、データを解析し dashMachineInfo を更新
        try:
            # PDFのバイトマップに従ってデータを抽出・変換
            # バイトオーダーは "big" (Motorola byte order) 

            # RPM (bytes 4:6)
            rpm_val = int.from_bytes(self.buffer[4:6], 'big')
            self.dashMachineInfo.setRpm(rpm_val)

            # Throttle Position (bytes 6:8, scale 0.1)
            tp_val = round(int.from_bytes(self.buffer[6:8], 'big') * 0.1, 1)
            self.dashMachineInfo.throttlePosition = tp_val

            # Engine Temperature (WaterTemp) (bytes 12:14, scale 0.1)
            wt_val = round(int.from_bytes(self.buffer[12:14], 'big') * 0.1, 1)
            self.dashMachineInfo.waterTemp = WaterTemp(int(wt_val))

            # Oil Temperature (bytes 26:28, scale 0.1)
            ot_val = round(int.from_bytes(self.buffer[26:28], 'big') * 0.1, 1)
            self.dashMachineInfo.oilTemp = OilTemp(int(ot_val))
            
            # Oil Pressure (bytes 28:30, scale 0.1)
            op_val = round(int.from_bytes(self.buffer[28:30], 'big') * 0.1, 1)
            self.dashMachineInfo.oilPress.oilPress = op_val
            
            # Gear Voltage (bytes 30:32, scale 0.01)
            gv_val = round(int.from_bytes(self.buffer[30:32], 'big') * 0.01, 2)
            self.dashMachineInfo.gearVoltage = GearVoltage(gv_val)

            # Battery Voltage (bytes 48:50, scale 0.01)
            bv_val = round(int.from_bytes(self.buffer[48:50], 'big') * 0.01, 2)
            self.dashMachineInfo.batteryVoltage = BatteryVoltage(bv_val)

            # Fuel Pressure (bytes 24:26, scale 0.1)
            fp_val = round(int.from_bytes(self.buffer[24:26], 'big') * 0.1, 1)
            self.dashMachineInfo.fuelPress = FuelPress(int(fp_val))

            # Fuel Effective Pulse Width (bytes 112:114, scale 0.5 µs)
            fepw_val = round(int.from_bytes(self.buffer[112:114], 'big') * 0.5, 1)
            self.dashMachineInfo.fuelEffectivePulseWidth = fepw_val
        except IndexError:
            # 万が一、パケットの長さが足りない場合に備えます。
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
        # CAN IDの小さい方から順に並べる
        self.canIdLength = sorted(
            self.MOTEC_CAN_ID_LENGTHS + self.DATA_LOGGER_CAN_ID_LENGTHS,
            key=lambda il: il.id,
        )

        # 最初は何も入っていない
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
