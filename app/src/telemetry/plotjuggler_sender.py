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
        
        # 設定からターゲットIPリストを取得
        self.target_ips = config.PLOTJUGGLER_TARGET_IPS
        self.target_port = config.PLOTJUGGLER_PORT
        
        logger.info(f"PlotJuggler Sender initialized. Targets: {self.target_ips}:{self.target_port}")

    def start(self) -> None:
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
            data = {
                # "timestamp": time.time(),  # 無効化中
                
                # --- 基本情報 ---
                "RPM": int(info.rpm),
                "Throttle (%)": info.throttlePosition,
                "Water Temp (C)": int(info.waterTemp),
                "Oil Temp (C)": int(info.oilTemp),
                "Oil Press (bar)": info.oilPress.oilPress, 
                # "Fuel Press (kPa)": float(info.fuelPress), # 無効化中
                "Gear Volts (V)": float(info.gearVoltage),
                "Battery (V)": float(info.batteryVoltage),
                
                # ★追加: 新しい計測項目
                "Manifold Pressure (kPa)": getattr(info, "manifoldPressure", 0.0),
                "Lambda 1": getattr(info, "lambda1", 0.0),
                
                # --- 燃料情報 ---
                "Fuel Level (%)": fuel_percent,
                "Fuel Used (mL)": getattr(info, "fuelUsed", 0.0),
                
                # 積算消費量
                "Fuel Consumed Total (mL)": getattr(info, "fuelConsumedTotal", 0.0),

                # --- ラップタイム情報 ---
                # "Lap Count": info.lapCount,       # 無効化中
                # "Lap Time": info.currentLapTime   # 無効化中
            }

            # JSON変換
            json_payload = json.dumps(data).encode('utf-8')

            # 各ターゲットへ送信
            for ip in self.target_ips:
                try:
                    self.sock.sendto(json_payload, (ip, self.target_port))
                except OSError as e:
                    pass

        except Exception as e:
            logger.error(f"PlotJuggler send error: {e}")