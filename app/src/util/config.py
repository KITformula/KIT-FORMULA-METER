import os
import dotenv

# .env ファイルをロード
dotenv.load_dotenv()

# --- 既存の設定 ---
machineId = int(os.environ["MACHINE_ID"])
udpAddress = (os.environ["UDP_ADDRESS"], int(os.environ["UDP_PORT"]))
cloudRunApiEndpoint = os.environ["CLOUD_RUN_API_ENDPOINT"]
cloudMessageApiEndpoint = os.environ["CLOUD_MESSAGE_API_ENDPOINT"]
cloudLaptimeApiEndpoint = os.environ["CLOUD_LAPTIME_API_ENDPOINT"]

debug = os.getenv("DEBUG", "False").lower() == "true"

# --- 燃料計算用の設定値 ---
NUM_CYLINDERS = int(os.environ["NUM_CYLINDERS"])
INJECTOR_FLOW_RATE_CC_PER_MIN = float(os.environ["INJECTOR_FLOW_RATE_CC_PER_MIN"])
INITIAL_FUEL_ML = float(os.environ["INITIAL_FUEL_ML"])

# --- 燃料保存の周期 ---
FUEL_SAVE_INTERVAL_MS = int(os.environ.get("FUEL_SAVE_INTERVAL_MS", 1000))

# --- TPMS設定 ---
RTL433_FREQUENCY = os.environ.get("RTL433_FREQUENCY", "429.5M")
TPMS_ID_MAP = {
    "a61b44e3": "FR",
    "64f3850c": "FL",
    "766b4951": "RR",
    "74f4be1b": "RL"
}

# --- ★追加: InfluxDB 設定 ---
INFLUX_URL = os.environ.get("INFLUX_URL", "https://us-east-1-1.aws.cloud2.influxdata.com")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "Tz-c15zj_Bch8dInPyM70TjGNc56cOoh7nojMJclN63oXCg_v0RR_qEb8K3Kb9jB456z66cUo1ClirxGbu4IVA==")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "710d5a613ea796c2")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "Real-time telemetry")