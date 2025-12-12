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
        current_start_ml = self.fuel_store.load_state() or self.tank_capacity_ml

        # ★変更: インジェクター容量などの引数を削除
        self.fuel_calculator = FuelCalculator(
            tank_capacity_ml=self.tank_capacity_ml,
            current_remaining_ml=current_start_ml,
        )

        self.course_manager = CourseManager()
        self.lap_timer = LapTimer(self.course_manager)
        self.machine = Machine(self.fuel_calculator)

    def update(self, gps_data):
        self.lap_timer.update(gps_data, self.machine.canMaster.dashMachineInfo)

    def save_fuel_state(self):
        current_ml = self.fuel_calculator.remaining_fuel_ml
        self.fuel_store.save_state(current_ml)

    def reset_fuel(self):
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