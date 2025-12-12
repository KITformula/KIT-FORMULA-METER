import json
import logging
import time

import paho.mqtt.client as mqtt

from src.models.models import DashMachineInfo, GearType
from src.telemetry.sender_interface import TelemetrySender
from src.util import config

logger = logging.getLogger(__name__)

# ★プロジェクトの要求頻度: 100ms (0.1秒) に設定
SEND_INTERVAL_SEC = 0.1


class MqttTelemetrySender(TelemetrySender):
    """
    MQTT (HiveMQ Cloud) を利用して車両データをリアルタイム送信するクラス
    """

    def __init__(self):
        unique_id = f"pi-telemetry-{config.machineId}-{int(time.time() * 1000)}"

        self.client = mqtt.Client(
            client_id=unique_id,
            clean_session=True,
        )
        self.is_connected = False
        self._setup_client()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT Broker Connected successfully.")
            self.is_connected = True
        else:
            logger.error(f"MQTT Connection Failed. Return code: {rc}")
            self.is_connected = False

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            logger.warning("MQTT Disconnected unexpectedly. Attempting to reconnect...")

    def _setup_client(self):
        self.client.tls_set()
        self.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.will_set(
            f"{config.MQTT_TOPIC}/status",
            payload=f"Machine {config.machineId} Disconnected",
            qos=1,
            retain=False,
        )

    def start(self) -> None:
        try:
            self.client.connect(
                config.MQTT_BROKER_URL,
                config.MQTT_BROKER_PORT,
                keepalive=config.MQTT_KEEP_ALIVE_SEC,
            )
            self.client.loop_start()
            logger.info("MQTT loop started.")
        except Exception as e:
            logger.error(f"Failed to start MQTT connection: {e}")

    def stop(self) -> None:
        if self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT connection stopped.")

    def send(self, info: DashMachineInfo, fuel_percent: float, tpms_data: dict) -> None:
        if not self.is_connected:
            return

        def safe_val(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0

        payload_data = {}

        # --- 基本データ ---
        payload_data["rpm"] = int(safe_val(getattr(info, "rpm", 0)))
        payload_data["spd"] = safe_val(getattr(info, "speed", 0))

        gear_type = (
            getattr(info.gearVoltage, "gearType", GearType.NEUTRAL)
            if hasattr(info, "gearVoltage")
            else GearType.NEUTRAL
        )
        if gear_type == GearType.NEUTRAL:
            payload_data["gr"] = "N"
        else:
            payload_data["gr"] = str(gear_type.value)

        # --- センサーデータ ---
        payload_data["wt"] = round(safe_val(getattr(info, "waterTemp", 0)), 1)
        payload_data["ot"] = round(safe_val(getattr(info, "oilTemp", 0)), 1)
        payload_data["tp"] = round(safe_val(getattr(info, "throttlePosition", 0)), 1)

        oil_press_obj = getattr(info, "oilPress", None)
        if oil_press_obj and hasattr(oil_press_obj, "oilPress"):
            payload_data["op"] = round(safe_val(oil_press_obj.oilPress), 2)
        else:
            payload_data["op"] = 0.0

        payload_data["v"] = round(safe_val(getattr(info, "batteryVoltage", 0)), 1)

        # --- ラップタイム関連 ---
        payload_data["lc"] = int(safe_val(getattr(info, "lapCount", 0)))
        payload_data["clt"] = round(safe_val(getattr(info, "currentLapTime", 0)), 3)
        payload_data["ltd"] = round(safe_val(getattr(info, "lapTimeDiff", 0)), 3)

        # --- 燃料とTPMSデータ ---
        payload_data["fp"] = round(fuel_percent, 2)
        
        # もし積算使用量も送信したい場合は以下を追加
        # payload_data["fuel_used_L"] = round(safe_val(getattr(info, "fuelUsed", 0)) / 1000.0, 3)

        for wheel, data in tpms_data.items():
            wheel_key = wheel.lower()  # fr, fl, rr, rl
            payload_data[f"t_{wheel_key}_p"] = data.get("pressure_psi")
            payload_data[f"t_{wheel_key}_t"] = data.get("temperature_c")

        try:
            payload = json.dumps(payload_data, separators=(",", ":"))
            full_topic = f"{config.MQTT_TOPIC}/{config.machineId}"
            self.client.publish(full_topic, payload, qos=0)

        except Exception as e:
            logger.error(f"MQTT Publish Failed: {e}")