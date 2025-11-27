from datetime import timedelta
from enum import IntEnum


class RpmStatus(IntEnum):
    LOW = 0
    MIDDLE = 1
    HIGH = 2
    SHIFT = 3


class Rpm(int):
    LOW_THRESHOLD = 4000
    HIGH_THRESHOLD = 7000
    SHIFT_THRESHOLD = 9000
    MAX = 10000

    @property
    def status(self) -> RpmStatus:
        if self < self.LOW_THRESHOLD:
            return RpmStatus.LOW
        elif self < self.HIGH_THRESHOLD:
            return RpmStatus.MIDDLE
        elif self < self.SHIFT_THRESHOLD:
            return RpmStatus.HIGH
        else:
            return RpmStatus.SHIFT


class WaterTempStatus(IntEnum):
    LOW = 0
    MIDDLE = 1
    WARNING = 2
    HIGH = 3


class WaterTemp(int):
    LOW_THRESHOLD = 60
    MIDDLE_THRESHOLD = 100
    WARNING_THRESHOLD = 118

    @property
    def status(self) -> WaterTempStatus:
        if self < self.LOW_THRESHOLD:
            return WaterTempStatus.LOW
        elif self < self.MIDDLE_THRESHOLD:
            return WaterTempStatus.MIDDLE
        elif self < self.WARNING_THRESHOLD:
            return WaterTempStatus.WARNING
        else:
            return WaterTempStatus.HIGH


class OilTempStatus(IntEnum):
    LOW = 0
    MIDDLE = 1
    HIGH = 2


class OilTemp(int):
    LOW_THRESHOLD = 120
    HIGH_THRESHOLD = 140

    @property
    def status(self) -> OilTempStatus:
        if self < self.LOW_THRESHOLD:
            return OilTempStatus.LOW
        elif self < self.HIGH_THRESHOLD:
            return OilTempStatus.MIDDLE
        else:
            return OilTempStatus.HIGH


class OilPressStatus(IntEnum):
    LOW = 0
    MIDDLE = 1
    HIGH = 2


class OilPress:
    oilPress: float
    rpm: int

    COEFFICIENT_LOW = 0.00000172
    COEFFICIENT_HIGH = 0.00000241088030949

    def __init__(self):
        self.oilPress = 0.0
        self.rpm = 0

    @property
    def status(self) -> OilPressStatus:
        if self.oilPress < self.COEFFICIENT_LOW * self.rpm**2:
            return OilPressStatus.LOW
        elif self.oilPress < self.COEFFICIENT_HIGH * self.rpm**2:
            return OilPressStatus.MIDDLE
        else:
            return OilPressStatus.HIGH


class FuelPressStatus(IntEnum):
    LOW = 0
    HIGH = 1


class FuelPress(float):
    THRESHOLD = 50.0

    @property
    def status(self) -> FuelPressStatus:
        if self < self.THRESHOLD:
            return FuelPressStatus.LOW
        else:
            return FuelPressStatus.HIGH


class LapTime(timedelta):
    pass


class GearType(IntEnum):
    NEUTRAL = 0
    FIRST = 1
    SECOND = 2
    THIRD = 3
    TOP = 4
    FIFTH = 5
    SIXTH = 6


class GearVoltage(float):
    # EACH_VOLTAGES = [3.86, 4.20, 3.52, 2.84, 2.16, 1.50, 0.81]  # Normal
    EACH_VOLTAGES = [0.8, 1.53, 2.16, 2.84, 3.52]  # IST

    @property
    def gearType(self) -> GearType:
        deviations = [
            abs(self - eachVoltage) for eachVoltage in GearVoltage.EACH_VOLTAGES
        ]
        gearNum = deviations.index(min(deviations))
        return GearType(gearNum)

    @property
    def gearTypeString(self) -> str:
        g = self.gearType
        if g == GearType.NEUTRAL:
            return "N"
        else:
            return str(g)


def getGearType(voltage: float) -> GearType:
    EACH_VOLTAGES = [3.86, 4.20, 3.52, 2.84, 2.16, 1.50, 0.81]

    deviations = [abs(voltage - eachVoltage) for eachVoltage in EACH_VOLTAGES]
    gearNum = deviations.index(min(deviations))
    return GearType(gearNum)


class BatteryStatus(IntEnum):
    LOW = 0
    HIGH = 1


class BatteryVoltage(float):
    THRESHOLD = 11

    @property
    def status(self) -> BatteryStatus:
        if self < self.THRESHOLD:
            return BatteryStatus.LOW
        else:
            return BatteryStatus.HIGH


class BrakePress:
    front: float
    rear: float

    def __init__(self):
        self.front = 0.0
        self.rear = 0.0

    @property
    def bias(self) -> float:
        if self.front <= 0.0 and self.rear <= 0.0:
            return 0.0
        else:
            front = max(0.0, self.front)
            rear = max(0.0, self.rear)
            return round(100.0 * front / (front + rear), 1)


class DashMachineInfo:
    """
    車両の全情報を保持するデータクラス
    """

    lapCount: int
    currentLapTime: float  # リアルタイムの経過時間または確定したラップタイム
    lastLapTime: float
    lapTimeDiff: float  # 前周との差 (Δタイム)
    gpsQuality: int  # GPS品質

    rpm: Rpm
    speed: float  # ★追加: 速度フィールドを明示的に追加
    throttlePosition: float
    waterTemp: WaterTemp
    oilTemp: OilTemp
    oilPress: OilPress
    gearVoltage: GearVoltage
    batteryVoltage: BatteryVoltage
    fanEnabled: bool
    fuelPress: FuelPress
    brakePress: BrakePress

    fuelEffectivePulseWidth: float
    delta_t: float  # 前回のパケットからの経過時間

    sector_times: dict[int, float]
    sector_diffs: dict[int, float]

    def __init__(self) -> None:
        self.rpm = Rpm(0)
        self.speed = 0.0  # ★初期化
        self.throttlePosition = 0.0
        self.waterTemp = WaterTemp(0)
        self.oilTemp = OilTemp(0)
        self.oilPress = OilPress()
        self.gearVoltage = GearVoltage(GearVoltage.EACH_VOLTAGES[GearType.NEUTRAL])
        self.batteryVoltage = BatteryVoltage(0)
        self.fanEnabled = False
        self.fuelPress = FuelPress(0.0)
        self.brakePress = BrakePress()
        self.fuelEffectivePulseWidth = 0.0
        self.delta_t = 0.0

        self.lapCount = 0
        self.currentLapTime = 0.0
        self.lastLapTime = 0.0
        self.lapTimeDiff = 0.0
        self.gpsQuality = 0

        self.sector_times = {}
        self.sector_diffs = {}

    def setRpm(self, rpm: int):
        self.rpm = Rpm(rpm)
        self.oilPress.rpm = rpm

    def to_telemetry_payload(self) -> dict:
        """
        ★洗練ポイント: MQTT送信用の軽量JSON辞書を生成するメソッド
        送信ロジック側でガチャガチャ変換するのではなく、データ自身に変換させる。
        """
        gear_val = self.gearVoltage.gearType.value
        gear_str = "N" if gear_val == 0 else str(gear_val)

        return {
            # 基本情報
            "rpm": int(self.rpm),
            "spd": round(float(self.speed), 1),
            "gr": gear_str,
            # エンジン・センサー (小数点1桁に丸めて軽量化)
            "wt": round(float(self.waterTemp), 1),
            "ot": round(float(self.oilTemp), 1),
            "tp": round(float(self.throttlePosition), 1),
            "op": round(float(self.oilPress.oilPress), 2),  # 油圧はクラス内の属性を参照
            "v": round(float(self.batteryVoltage), 1),
            # ラップタイム関連
            "lc": int(self.lapCount),
            "clt": round(float(self.currentLapTime), 2),
            "ltd": round(float(self.lapTimeDiff), 2),
            # その他（必要なら追加）
            "fp": round(float(self.fuelPress), 1),
        }


class Message:
    text: str
    laptime: float

    def __init__(self) -> None:
        self.text = ""
        self.laptime = 0.0
