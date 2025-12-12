import threading


class FuelCalculator:
    """
    ECUから送られてくる「Fuel Used（使用量）」データを監視し、
    残燃料を管理するクラス。
    
    以前のようなパルス幅とRPMからの複雑な積分計算は行わず、
    ECUの計算結果を信頼して差分を反映します。
    """

    def __init__(
        self,
        tank_capacity_ml: float,
        current_remaining_ml: float,
    ):
        """
        - tank_capacity_ml: タンクの「満タン容量」 (ml)
        - current_remaining_ml: 「計算開始時点」の燃料残量 (ml)
        """
        # 満タンの定義 (パーセント計算用)
        self.tank_capacity_ml = max(0.0, tank_capacity_ml)

        # 計算のベースとなる残量
        self._start_remaining_ml = current_remaining_ml

        # このセッションでECUから報告された「使用量の増加分」の合計
        self.session_consumed_total = 0.0

        # 前回ECUから受け取った生の値 (差分計算用)
        self._last_ecu_fuel_used_raw = None

        # 排他制御用のロック
        self._lock = threading.Lock()

    @property
    def remaining_fuel_ml(self) -> float:
        """
        現在の燃料残量を返す。
        (初期残量 - このセッションでの増加消費量)
        """
        with self._lock:
            current_ml = self._start_remaining_ml - self.session_consumed_total
            return max(0.0, min(self.tank_capacity_ml, current_ml))

    @remaining_fuel_ml.setter
    def remaining_fuel_ml(self, value: float):
        """
        現在の燃料残量をリセットする（給油時など）。
        これまでのセッション消費量をリセットし、ベース値を更新する。
        """
        with self._lock:
            self._start_remaining_ml = value
            self.session_consumed_total = 0.0
            # リセット時は差分計算の基準もリセットしたほうが安全だが、
            # ECUの値自体は飛び飛びにならないので、_last_ecu_fuel_used_raw は維持でOK。

    @property
    def remaining_fuel_percent(self) -> float:
        """
        現在の燃料残量をパーセンテージで返す。
        """
        if self.tank_capacity_ml <= 0:
            return 0.0

        percentage = (self.remaining_fuel_ml / self.tank_capacity_ml) * 100.0
        return max(0.0, min(100.0, percentage))

    def update_from_ecu(self, current_fuel_used_raw: float):
        """
        ECUから受信した「Fuel Used」の値を入力し、
        前回値との差分を消費量として加算する。
        
        Args:
            current_fuel_used_raw (float): ECUからの生データ (単位はECU設定に依存、ここではml想定)
        """
        with self._lock:
            # 初回受信時は基準値をセットするだけで、消費計算はしない
            if self._last_ecu_fuel_used_raw is None:
                self._last_ecu_fuel_used_raw = current_fuel_used_raw
                return

            # 差分を計算
            diff = current_fuel_used_raw - self._last_ecu_fuel_used_raw

            # 正常な増加の場合のみ加算
            # (ECUリセット等で値が若返った場合は無視するか、新しい基準としてリセットする)
            if diff >= 0:
                self.session_consumed_total += diff
            else:
                # ECU側の値がリセットされたとみなし、基準値を更新
                # (消費量の加算は行わない)
                print(f"FuelCalc: ECU reset detected ({self._last_ecu_fuel_used_raw} -> {current_fuel_used_raw})")
            
            # 今回の値を次回用に保存
            self._last_ecu_fuel_used_raw = current_fuel_used_raw