import threading


class FuelCalculator:
    """
    インジェクターの性能値などのパラメータを元に、
    リアルタイムデータから燃料消費量を計算する専門家。
    """

    def __init__(
        self,
        injector_flow_rate_cc_per_min: float,
        num_cylinders: int,
        tank_capacity_ml: float,
        current_remaining_ml: float,
    ):
        """
        計算に必要な固定パラメータを設定して初期化します。
        - injector_flow_rate_cc_per_min: インジェクターの噴射量 (cc/min)
        - num_cylinders: エンジンの気筒数
        - tank_capacity_ml: タンクの「満タン容量」 (ml)
        - current_remaining_ml: 「計算開始時点」の燃料残量 (ml)
        """
        # 1. 必要なパラメータを外部から受け取り、自分の持ち物にする
        self.injector_flow_rate_cc_per_ms = injector_flow_rate_cc_per_min / 60 / 1000
        self.num_cylinders = num_cylinders

        # 満タンの定義 (パーセント計算用)
        self.tank_capacity_ml = max(0.0, tank_capacity_ml)  # 0未満にならないように

        # 計算のベースとなる残量
        self._start_remaining_ml = current_remaining_ml

        # 2. このインスタンスが起動してからの「積算消費量」
        self.session_consumed_cc = 0.0

        # ★ 追加: 排他制御用のロック (スレッドセーフ対策)
        self._lock = threading.Lock()

    @property
    def remaining_fuel_ml(self) -> float:
        """
        現在の燃料残量を計算して返す。
        (計算開始時の残量 - このセッションでの消費量)
        """
        # 読み込み時もロックを取得して整合性を保つ
        with self._lock:
            # ccとmlは等価
            current_ml = self._start_remaining_ml - self.session_consumed_cc
            # タンク容量以上になったり、0未満になったりしないように制限
            return max(0.0, min(self.tank_capacity_ml, current_ml))

    # ★★★ 修正: セッターを追加して値を更新できるようにする ★★★
    @remaining_fuel_ml.setter
    def remaining_fuel_ml(self, value: float):
        """
        現在の燃料残量をリセットする。
        これまでのセッション消費量を0にリセットし、
        開始時の残量を新しい値に設定する。
        """
        # 書き込み時もロックを取得
        with self._lock:
            self._start_remaining_ml = value
            self.session_consumed_cc = 0.0

    @property
    def remaining_fuel_percent(self) -> float:
        """
        現在の燃料残量をパーセンテージで計算して返す。
        (計算の基準は「満タン容量」)
        """
        # ゼロ除算を防ぐ
        if self.tank_capacity_ml <= 0:
            return 0.0

        # (現在の残量 / 満タン容量) * 100
        # self.remaining_fuel_ml へのアクセス自体がロックされているため、ここはロック不要
        percentage = (self.remaining_fuel_ml / self.tank_capacity_ml) * 100.0

        return max(0.0, min(100.0, percentage))

    def update_consumption(
        self, rpm: int, effective_pulse_width_us: float, delta_t_sec: float
    ):
        """
        新しいデータを受け取り、その間の消費量を計算して積算する。
        """

        if rpm <= 0 or effective_pulse_width_us <= 0 or delta_t_sec <= 0:
            return

        # インジェクター噴射回数(回/秒) = (RPM / 60) / 2 (4ストロークエンジンの場合、2回転に1回噴射)
        # ※シーケンシャル噴射などを想定。同時噴射の場合は要調整だが、ここでは一般的な計算式を使用。
        injections_per_second_per_cylinder = (rpm / 60.0) / 2.0

        # 1秒あたりの総噴射時間(ms) = 1回あたりの噴射時間(ms) * 1秒あたりの回数
        total_injection_time_ms_per_second = (
            effective_pulse_width_us / 1000.0
        ) * injections_per_second_per_cylinder

        # 1気筒あたりの消費量(cc/sec) = 総噴射時間(ms) * 流量(cc/ms)
        fuel_consumption_cc_per_second_per_cylinder = (
            total_injection_time_ms_per_second * self.injector_flow_rate_cc_per_ms
        )

        # エンジン全体での消費量(cc/sec)
        total_consumption_cc_per_second = (
            fuel_consumption_cc_per_second_per_cylinder * self.num_cylinders
        )

        # 経過時間(delta_t)での消費量
        fuel_used_in_delta_t = total_consumption_cc_per_second * delta_t_sec

        # ★ 修正: このセッションでの消費量として積算（ロックを取得）
        with self._lock:
            self.session_consumed_cc += fuel_used_in_delta_t