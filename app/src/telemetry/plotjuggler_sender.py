import json
import socket
import time
import logging
from src.models.models import DashMachineInfo
from src.telemetry.sender_interface import TelemetrySender
from src.util import config

logger = logging.getLogger(__name__)

class PlotJugglerSender(TelemetrySender):
    """
    PlotJuggler等の外部ツールへUDPでJSONデータを送信するクラス
    """
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 設定からターゲットIPリストを取得 (カンマ区切りで環境変数から読み込む想定)
        self.target_ips = config.PLOTJUGGLER_TARGET_IPS
        self.target_port = config.PLOTJUGGLER_PORT
        
        logger.info(f"PlotJuggler Sender initialized. Targets: {self.target_ips}:{self.target_port}")

    def start(self) -> None:
        # UDPなので接続処理は不要
        pass

    def stop(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass

    def send(self, info: DashMachineInfo, fuel_percent: float, tpms_data: dict) -> None:
        """
        DashMachineInfoのデータをJSONに変換してUDP送信する
        """
        try:
            # DashMachineInfo から PlotJuggler 用の辞書を作成
            # message.txt のキー名に合わせています [cite: 6, 7, 8]
            data = {
                "timestamp": time.time(),
                "RPM": int(info.rpm),
                "Throttle (%)": info.throttlePosition,
                "Water Temp (C)": int(info.waterTemp),
                "Oil Temp (C)": int(info.oilTemp),
                "Oil Press (bar)": info.oilPress.oilPress, # 単位注意: 元コードはbar想定、モデルの実装に合わせてください
                "Fuel Press (kPa)": float(info.fuelPress),
                "Gear Volts (V)": float(info.gearVoltage),
                "Battery (V)": float(info.batteryVoltage),
                
                # 追加データ
                "Fuel Level (%)": fuel_percent,
                "Lap Count": info.lapCount,
                "Lap Time": info.currentLapTime
            }

            # JSON変換
            json_payload = json.dumps(data).encode('utf-8')

            # 各ターゲットへ送信 [cite: 8]
            for ip in self.target_ips:
                try:
                    self.sock.sendto(json_payload, (ip, self.target_port))
                except OSError as e:
                    # ネットワーク到達不能などはログに出しすぎないように注意
                    pass

        except Exception as e:
            logger.error(f"PlotJuggler send error: {e}")