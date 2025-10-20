class FuelCalculator:
    """
    インジェクターの性能値などのパラメータを元に、
    リアルタイムデータから燃料消費量を計算する専門家。
    """
   
    
    INITIAL_FUEL_ML: float = 4500.0



    def __init__(self, injector_flow_rate_cc_per_min: float, num_cylinders: int):
        """
        計算に必要な固定パラメータを設定して初期化します。
        - injector_flow_rate_cc_per_min: インジェクターの噴射量 (cc/min)
        - num_cylinders: エンジンの気筒数
        """
        # 1. 必要なパラメータを外部から受け取り、自分の持ち物にする
        #    計算しやすいように、単位を cc/ms に変換しておく
        self.injector_flow_rate_cc_per_ms = injector_flow_rate_cc_per_min / 60 / 1000
        self.num_cylinders = num_cylinders
        
        # 2. 計算結果を積算していくための変数
        self.total_fuel_consumed_cc = 0.0
    
    @property
    def remaining_fuel_ml(self) -> float:
        """
        初期容量から積算消費量を引いた、現在の燃料残量を計算して返す。
        """
        # ccとmlは等価なので、そのまま引き算でOK
        return self.INITIAL_FUEL_ML - self.total_fuel_consumed_cc
    
    @property
    def remaining_fuel_percent(self) -> float:
        """
        現在の燃料残量をパーセンテージで計算して返す。
        """
        # ゼロ除算を防ぐ
        if self.INITIAL_FUEL_ML <= 0:
            return 0.0
        
        percentage = (self.remaining_fuel_ml / self.INITIAL_FUEL_ML) * 100.0
        
        # 燃料が0%未満になったり、100%を超えたりしないように値を制限
        return max(0.0, min(100.0, percentage))

    def update_consumption(self, rpm: int, effective_pulse_width_us: float, delta_t_sec: float):
        """
        新しいデータを受け取り、その間の消費量を計算して積算する。
        - rpm: エンジン回転数
        - effective_pulse_width_us: インジェクター有効噴射時間 (マイクロ秒)
        - delta_t_sec: 前回のデータからの経過時間 (秒)
        """
        # エンジンが停止している場合などは計算しない
        if rpm <= 0 or effective_pulse_width_us <= 0 or delta_t_sec <= 0:
            return

        # --- ここからが計算の核心 ---
        # 1秒あたりの噴射回数 (4ストロークエンジンの場合)
        injections_per_second_per_cylinder = (rpm / 60.0) / 2.0
        
        # 1秒あたりの総噴射時間 [ms/秒]
        # µsをmsに変換するために1000で割る
        total_injection_time_ms_per_second = (effective_pulse_width_us / 1000.0) * injections_per_second_per_cylinder
        
        # 1気筒・1秒あたりの燃料消費量 [cc/秒]
        fuel_consumption_cc_per_second_per_cylinder = total_injection_time_ms_per_second * self.injector_flow_rate_cc_per_ms
        
        # エンジン全体の燃料消費量 [cc/秒]
        total_consumption_cc_per_second = fuel_consumption_cc_per_second_per_cylinder * self.num_cylinders
        
        # 経過時間(delta_t)ぶんの消費量を計算して、総消費量に加算する
        fuel_used_in_delta_t = total_consumption_cc_per_second * delta_t_sec
        self.total_fuel_consumed_cc += fuel_used_in_delta_t
