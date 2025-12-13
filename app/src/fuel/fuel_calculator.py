import threading


class FuelCalculator:
    """
    ECUから送られてくる「Fuel Used」データの差分を積み上げ、
    残量と合計消費量を管理するクラス。
    """

    def __init__(
        self,
        tank_capacity_ml: float,
        current_remaining_ml: float,
        initial_consumed_total: float = 0.0, # ★追加引数
    ):
        # 満タン容量
        self.tank_capacity_ml = max(0.0, tank_capacity_ml)

        # 計算のベースとなる残量 (今回のセッション開始時)
        self._start_remaining_ml = current_remaining_ml
        
        # 今回のセッションでの消費量 (残量計算用)
        self._session_consumed = 0.0

        # ★ 表示用の合計消費量 (前回保存分 + 今回の消費分)
        self._base_consumed_total = initial_consumed_total

        # 前回ECUから受け取った生の値
        self._last_ecu_fuel_used_raw = None

        self._lock = threading.Lock()

    @property
    def remaining_fuel_ml(self) -> float:
        """現在の燃料残量を返す"""
        with self._lock:
            # 残量 = (起動時の残量) - (今回減った分)
            current_ml = self._start_remaining_ml - self._session_consumed
            return max(0.0, min(self.tank_capacity_ml, current_ml))

    @remaining_fuel_ml.setter
    def remaining_fuel_ml(self, value: float):
        """燃料残量をリセットする（給油時など）"""
        with self._lock:
            self._start_remaining_ml = value
            self._session_consumed = 0.0
            
            # ★ リセット時は合計消費量も0に戻す
            self._base_consumed_total = 0.0 

    @property
    def session_consumed_total(self) -> float:
        """
        外部公開用の合計消費量 (保存分 + 今回分)
        ※変数名は変えずに中身のロジックを変えることで、他のファイルを修正しなくて済むようにします
        """
        with self._lock:
            return self._base_consumed_total + self._session_consumed

    @property
    def remaining_fuel_percent(self) -> float:
        if self.tank_capacity_ml <= 0:
            return 0.0
        percentage = (self.remaining_fuel_ml / self.tank_capacity_ml) * 100.0
        return max(0.0, min(100.0, percentage))

    def update_from_ecu(self, current_fuel_used_raw: float):
        with self._lock:
            if self._last_ecu_fuel_used_raw is None:
                self._last_ecu_fuel_used_raw = current_fuel_used_raw
                return

            diff = current_fuel_used_raw - self._last_ecu_fuel_used_raw

            if diff >= 0:
                self._session_consumed += diff
            else:
                print(f"FuelCalc: ECU reset detected ({self._last_ecu_fuel_used_raw} -> {current_fuel_used_raw})")
            
            self._last_ecu_fuel_used_raw = current_fuel_used_raw