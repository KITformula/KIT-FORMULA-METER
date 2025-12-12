import os
import dotenv

# .env ファイルをロード
dotenv.load_dotenv()

# --- 基本設定 ---
machineId = int(os.environ.get("MACHINE_ID", 1))
debug = os.getenv("DEBUG", "False").lower() == "true"

# --- API設定 ---
udpAddress = (
    os.environ.get("UDP_ADDRESS", "127.0.0.1"),
    int(os.environ.get("UDP_PORT", 5005)),
)
cloudRunApiEndpoint = os.environ.get("CLOUD_RUN_API_ENDPOINT", "")
cloudMessageApiEndpoint = os.environ.get("CLOUD_MESSAGE_API_ENDPOINT", "")
cloudLaptimeApiEndpoint = os.environ.get("CLOUD_LAPTIME_API_ENDPOINT", "")

# --- 燃料計算設定 ---
INITIAL_FUEL_ML = float(os.environ.get("INITIAL_FUEL_ML", 4500.0))
FUEL_SAVE_INTERVAL_MS = int(os.environ.get("FUEL_SAVE_INTERVAL_MS", 1000))

# ★変更: ECUからの "Fuel Used" (Raw) を ml に変換する係数
# ユーザー指定の実測値係数
FUEL_USED_SCALING = float(os.environ.get("FUEL_USED_SCALING", 0.1666666667))

# --- TPMS設定 ---
RTL433_FREQUENCY = os.environ.get("RTL433_FREQUENCY", "429.5M")
TPMS_ID_MAP = {"a61b44e3": "FR", "64f3850c": "FL", "766b4951": "RR", "74f4be1b": "RL"}

# --- GPS設定 ---
GPS_PORT = os.environ.get("GPS_PORT", "/dev/ttyACM0")
GPS_BAUD = int(os.environ.get("GPS_BAUD", 115200))
GPS_LAP_RADIUS_METERS = float(os.environ.get("GPS_LAP_RADIUS_METERS", 3.0))
GPS_LAP_COOLDOWN_SEC = float(os.environ.get("GPS_LAP_COOLDOWN_SEC", 10.0))

# --- MQTT 設定 ---
MQTT_BROKER_URL = os.environ.get(
    "MQTT_BROKER_URL", "8560a3bce8ff43bb92829fea55036ac1.s1.eu.hivemq.cloud"
)
MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", 8883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "kitformula")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "Kitformula-2026")
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "vehicle/telemetry")
MQTT_KEEP_ALIVE_SEC = int(os.environ.get("MQTT_KEEP_ALIVE_SEC", 10))

# --- PlotJuggler / UDP Telemetry 設定 ---
# 複数のIPに送る場合はカンマ区切りで指定
# message.txt にあったIPをデフォルト値として設定
_ips_str = os.environ.get("PLOTJUGGLER_TARGET_IPS", "100.94.77.77,100.86.101.38")
PLOTJUGGLER_TARGET_IPS = [ip.strip() for ip in _ips_str.split(",") if ip.strip()]

PLOTJUGGLER_PORT = int(os.environ.get("PLOTJUGGLER_PORT", 9870))