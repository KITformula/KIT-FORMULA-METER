import logging
import json
import time

import paho.mqtt.client as mqtt

from src.telemetry.sender_interface import TelemetrySender
from src.models.models import DashMachineInfo, GearType 
from src.util import config 

logger = logging.getLogger(__name__)

# ★プロジェクトの要求頻度: 100ms (0.1秒) に設定
SEND_INTERVAL_SEC = 0.1 

class MqttTelemetrySender(TelemetrySender):
    """
    MQTT (HiveMQ Cloud) を利用して車両データをリアルタイム送信するクラス
    """
    
    def __init__(self):
        # ★修正箇所1: 毎回ユニークなIDを生成し、clean_session=Trueを設定
        # これにより、切断時にブローカー上のセッションが即座に消え、累積を防ぎます。
        # publisher_ + 現在時刻(ミリ秒)
        unique_id = f"pi-telemetry-{config.machineId}-{int(time.time() * 1000)}"
        
        self.client = mqtt.Client(
            client_id=unique_id,
            clean_session=True  # ★セッションを累積させない設定
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
        # 1. TLS/SSLを有効化
        self.client.tls_set()
        # 2. 認証情報を設定
        self.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        # 3. コールバックを設定
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        # 4. 自動再接続設定
        self.client.reconnect_delay_set(min_delay=1, max_delay=30) 
        
        # 5. LWT (Last Will)
        self.client.will_set(
            f"{config.MQTT_TOPIC}/status", 
            payload=f"Machine {config.machineId} Disconnected", 
            qos=1, 
            retain=False
        )

    def start(self) -> None:
        """接続とバックグラウンドループの開始"""
        try:
            # 4G環境の安定化のため、Keep Aliveは10秒に設定
            self.client.connect(
                config.MQTT_BROKER_URL, 
                config.MQTT_BROKER_PORT, 
                keepalive=config.MQTT_KEEP_ALIVE_SEC 
            )
            self.client.loop_start() 
            logger.info("MQTT loop started.")
        except Exception as e:
            logger.error(f"Failed to start MQTT connection: {e}")

    def stop(self) -> None:
        """切断とスレッドの停止"""
        if self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT connection stopped.")

    def send(self, info: DashMachineInfo, fuel_percent: float, tpms_data: dict) -> None:
        """車両データをMQTTで送信 (Publish)"""
        if not self.is_connected:
            return

        # ★安全に値を数値に変換するヘルパー関数
        def safe_val(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0

        # ペイロードの作成（キー名は短縮形を使用）
        payload_data = {}

        # --- 基本データ ---
        payload_data['rpm'] = int(safe_val(getattr(info, 'rpm', 0)))
        payload_data['spd'] = safe_val(getattr(info, 'speed', 0))
        
        # ギアの取得ロジック (GearVoltageクラスから判定)
        gear_type = getattr(info.gearVoltage, 'gearType', GearType.NEUTRAL) if hasattr(info, 'gearVoltage') else GearType.NEUTRAL
        if gear_type == GearType.NEUTRAL:
            payload_data['gr'] = "N"
        else:
            payload_data['gr'] = str(gear_type.value)

        # --- センサーデータ ---
        # models.py の定義に合わせて属性名を修正
        
        # WaterTemp(int) なので int() や float() で値化可能
        payload_data['wt'] = round(safe_val(getattr(info, 'waterTemp', 0)), 1)
        
        # OilTemp(int) なので同様
        payload_data['ot'] = round(safe_val(getattr(info, 'oilTemp', 0)), 1)
        
        # throttlePosition は float
        payload_data['tp'] = round(safe_val(getattr(info, 'throttlePosition', 0)), 1)
        
        # OilPress はクラス。内部に .oilPress という float 属性を持っている
        oil_press_obj = getattr(info, 'oilPress', None)
        if oil_press_obj and hasattr(oil_press_obj, 'oilPress'):
            payload_data['op'] = round(safe_val(oil_press_obj.oilPress), 2)
        else:
            payload_data['op'] = 0.0
        
        # BatteryVoltage(float)
        payload_data['v']  = round(safe_val(getattr(info, 'batteryVoltage', 0)), 1)

        # --- ラップタイム関連 ---
        payload_data['lc']  = int(safe_val(getattr(info, 'lapCount', 0)))
        payload_data['clt'] = round(safe_val(getattr(info, 'currentLapTime', 0)), 3)
        # models.pyには lastLapTime がないので lapTimeDiff を送るか、必要なら追加
        payload_data['ltd'] = round(safe_val(getattr(info, 'lapTimeDiff', 0)), 3) 
        
        # --- 燃料とTPMSデータ ---
        payload_data['fp'] = round(fuel_percent, 2)
        
        for wheel, data in tpms_data.items():
            wheel_key = wheel.lower() # fr, fl, rr, rl
            payload_data[f"t_{wheel_key}_p"] = data.get('pressure_psi')
            payload_data[f"t_{wheel_key}_t"] = data.get('temperature_c')
            
        
        # データ送信
        try:
            # データ量削減のため separators を使用
            payload = json.dumps(payload_data, separators=(',', ':'))
            full_topic = f"{config.MQTT_TOPIC}/{config.machineId}"
            self.client.publish(full_topic, payload, qos=0)
            
        except Exception as e:
            logger.error(f"MQTT Publish Failed: {e}")

        # GUI周期に任せるため sleep なし