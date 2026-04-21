from abc import ABC, abstractmethod

class IPwmController(ABC):
    @abstractmethod
    def set_duty_cycle(self, percent: int):
        pass
    
    @abstractmethod
    def stop(self):
        pass

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

class RPiPwmController(IPwmController):
    def __init__(self, pin: int, frequency: int = 10000):
        self.pin = pin
        self.frequency = frequency
        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            # ラズパイのハードの制約内で10kHzで動作させます
            self.pwm = GPIO.PWM(self.pin, self.frequency)
            self.pwm.start(0)
        else:
            print(f"[Mock] PWM started on pin {pin} at {frequency}Hz")
            self.pwm = None

    def set_duty_cycle(self, percent: int):
        if not (0 <= percent <= 100):
            percent = max(0, min(100, percent))
        
        if GPIO_AVAILABLE and self.pwm:
            self.pwm.ChangeDutyCycle(percent)
        else:
            print(f"[Mock] PWM Pin {self.pin} set to {percent}%")

    def stop(self):
        if GPIO_AVAILABLE and self.pwm:
            self.pwm.stop()