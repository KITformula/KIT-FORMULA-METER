import threading
import queue
import time
import logging
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from src.util import config
from src.models.models import DashMachineInfo
from src.telemetry.sender_interface import TelemetrySender

logger = logging.getLogger(__name__)

class InfluxDbSender(TelemetrySender):
    def __init__(self):
        self.queue = queue.Queue(maxsize=200)
        self.running = False
        self.thread = None
        self.client = None
        self.write_api = None

    def start(self) -> None:
        try:
            self.client = InfluxDBClient(
                url=config.INFLUX_URL,
                token=config.INFLUX_TOKEN,
                org=config.INFLUX_ORG,
                timeout=5000
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            
            self.running = True
            self.thread = threading.Thread(target=self._worker, daemon=True)
            self.thread.start()
            
            logger.info(f"★ InfluxDB Connected: {config.INFLUX_ORG} / {config.INFLUX_BUCKET}")
            
        except Exception as e:
            logger.error(f"InfluxDB Init Error: {e}")

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.client:
            self.client.close()
        logger.info("★ InfluxDB Sender Stopped")

    def send(self, info: DashMachineInfo, fuel_percent: float, tpms_data: dict) -> None:
        if not self.running:
            return

        try:
            # --- データ変換 ---
            # ★ 修正ポイント: int() を float() に変更して型不一致エラーを回避
            point = Point("vehicle_data") \
                .tag("machine_id", str(config.machineId)) \
                .field("rpm", float(info.rpm)) \
                .field("water_temp", float(info.waterTemp)) \
                .field("oil_temp", float(info.oilTemp)) \
                .field("oil_press", float(info.oilPress.oilPress)) \
                .field("fuel_press", float(info.fuelPress)) \
                .field("gear", str(info.gearVoltage.gearTypeString)) \
                .field("battery_voltage", float(info.batteryVoltage)) \
                .field("fuel_remaining_percent", float(fuel_percent)) \
                .field("lap_count", int(info.lapCount)) \
                .field("current_lap_time", float(info.currentLapTime)) \
                .field("delta_t", float(info.delta_t))

            for sensor_id, data in tpms_data.items():
                position = config.TPMS_ID_MAP.get(sensor_id, sensor_id)
                if "pressure_kPa" in data:
                    point.field(f"tpms_{position}_press", float(data["pressure_kPa"]))
                if "temperature_C" in data:
                    point.field(f"tpms_{position}_temp", float(data["temperature_C"]))

            if self.queue.full():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    pass
            
            self.queue.put(point)

        except Exception as e:
            logger.error(f"Telemetry build error: {e}")

    def _worker(self):
        logger.info("★ Sender Thread Started")
        while self.running:
            try:
                # 1. データ取得
                point = self.queue.get(timeout=0.5)
                
                # 2. 書き込み実行
                self.write_api.write(
                    bucket=config.INFLUX_BUCKET,
                    org=config.INFLUX_ORG,
                    record=point
                )
                
                # 3. 成功ログ (頻繁に出るので確認後はコメントアウト推奨)
                logger.info(f"✔ Sent to InfluxDB! (Queue size: {self.queue.qsize()})")
                
                self.queue.task_done()
            
            except queue.Empty:
                continue
            except Exception as e:
                # 4. 失敗ログ
                logger.error(f"❌ Influx Write Error: {e}")
                time.sleep(1)