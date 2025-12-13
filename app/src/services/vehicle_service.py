from src.fuel.fuel_calculator import FuelCalculator
from src.race.lap_timer import LapTimer
from src.race.course_manager import CourseManager
from src.machine.machine import Machine
from src.util import config
from src.util.fuel_store import FuelStore


class VehicleService:
    def __init__(self):
        self.fuel_store = FuelStore()
        self.tank_capacity_ml = config.INITIAL_FUEL_ML
        
        # ★変更: load_stateが2つの値を返すようになったので受け取る
        loaded_remaining, loaded_consumed = self.fuel_store.load_state()
        
        # データがない場合は初期値
        current_start_ml = loaded_remaining if loaded_remaining is not None else self.tank_capacity_ml
        
        self.fuel_calculator = FuelCalculator(
            tank_capacity_ml=self.tank_capacity_ml,
            current_remaining_ml=current_start_ml,
            initial_consumed_total=loaded_consumed # ★これcalcに渡す
        )

        self.course_manager = CourseManager()
        self.lap_timer = LapTimer(self.course_manager)
        self.machine = Machine(self.fuel_calculator)

    def update(self, gps_data):
        self.lap_timer.update(gps_data, self.machine.canMaster.dashMachineInfo)

    def save_fuel_state(self):
        # ★変更: 残量と、合計消費量の両方を保存する
        current_ml = self.fuel_calculator.remaining_fuel_ml
        total_consumed = self.fuel_calculator.session_consumed_total
        self.fuel_store.save_state(current_ml, total_consumed)

    def reset_fuel(self):
        # 残量を満タンにし、消費量を0リセット
        self.fuel_calculator.remaining_fuel_ml = self.tank_capacity_ml
        self.save_fuel_state()

    def set_target_laps(self, laps: int):
        print(f"VehicleService: Setting target laps to {laps}")
        self.lap_timer.set_target_laps(laps)
        self.dash_info.targetLaps = laps

    @property
    def dash_info(self):
        return self.machine.canMaster.dashMachineInfo

    @property
    def fuel_percentage(self):
        return self.fuel_calculator.remaining_fuel_percent