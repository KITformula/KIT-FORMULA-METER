from PyQt5.QtCore import QObject, pyqtSignal, Qt
from src.tpms.tpms_worker import TpmsWorker
from src.gps.gps_worker import GpsWorker
from src.gopro.gopro_worker import GoProWorker
from src.hardware.encoder_worker import EncoderWorker
from src.hardware.pwm_controller import RPiPwmController # ★追加
from src.util import config
import threading

class HardwareService(QObject):
    tpms_updated = pyqtSignal(dict)
    gps_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tpms_worker = TpmsWorker(
            frequency=config.RTL433_FREQUENCY,
            id_map=config.TPMS_ID_MAP,
            debug_mode=config.debug,
        )
        self.tpms_worker.data_updated.connect(self.tpms_updated)

        self.gps_port = getattr(config, "GPS_PORT", "COM6")
        self.gps_baud = getattr(config, "GPS_BAUD", 115200)

        self.gps_worker = GpsWorker(
            self.gps_port, self.gps_baud, debug_mode=config.debug
        )
        self.gps_worker.data_received.connect(self.gps_updated)
        self.gps_worker.error_occurred.connect(lambda err: print(f"GPS Error: {err}"))

        self.gopro_worker = GoProWorker()
        self.encoder_worker = EncoderWorker(pin_a=20, pin_b=21, pin_sw=18)
        self.gps_thread = None

        # ★追加: PWMコントローラーの初期化 (10kHz)
        self.radiator_fan = RPiPwmController(pin=12, frequency=10000)
        self.water_pump = RPiPwmController(pin=13, frequency=10000)

    def start(self):
        self.tpms_worker.start()

        if self.gps_worker:
            self.gps_thread = threading.Thread(target=self.gps_worker.run, daemon=True)
            self.gps_thread.start()


    def set_radiator_fan(self, percent: int):
        self.radiator_fan.set_duty_cycle(100 - percent)

    def set_water_pump(self, percent: int):
        self.water_pump.set_duty_cycle(100 - percent)
    
    def stop(self):
        if self.tpms_worker:
            self.tpms_worker.stop()
        if self.gps_worker:
            self.gps_worker.stop()
        if self.encoder_worker:
            self.encoder_worker.stop()
        if self.gopro_worker:
            self.gopro_worker.stop()
        # ★追加
        self.radiator_fan.stop()
        self.water_pump.stop()
        
        # クリーンアップ (モック環境ではない場合)
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except ImportError:
            pass