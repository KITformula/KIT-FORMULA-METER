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

# --- 燃料保存の周期を追加 ---
# .envから読み込む。
FUEL_SAVE_INTERVAL_MS = int(os.environ.get("FUEL_SAVE_INTERVAL_MS"))