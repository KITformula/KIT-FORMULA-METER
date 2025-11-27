from PyQt5.QtCore import QObject, pyqtSignal
from gpiozero import RotaryEncoder, Button  # Buttonを追加
import logging

logger = logging.getLogger(__name__)


class EncoderWorker(QObject):
    rotated_cw = pyqtSignal()
    rotated_ccw = pyqtSignal()
    button_pressed = pyqtSignal()  # これを追加

    def __init__(self, pin_a=27, pin_b=17, pin_sw=22, parent=None):
        super().__init__(parent)
        self.rotor = None
        self.button = None

        try:
            # ロータリーエンコーダー初期化
            self.rotor = RotaryEncoder(a=pin_a, b=pin_b, max_steps=0)
            self.rotor.when_rotated = self._on_rotate
            self.last_steps = 0

            # スイッチピンが指定されていれば初期化
            if pin_sw is not None:
                # ★修正: bounce_time を設定してチャタリング(誤検知)を防ぐ
                # 0.05秒(50ms)以内の信号変化を無視します
                self.button = Button(pin_sw, bounce_time=0.05)
                self.button.when_pressed = self._on_button_press

            logger.info(f"Encoder init: A={pin_a}, B={pin_b}, SW={pin_sw}")
        except Exception as e:
            logger.error(f"GPIO Init Error: {e}")

    def _on_rotate(self):
        if self.rotor is None:
            return
        current = self.rotor.steps
        if current > self.last_steps:
            self.rotated_cw.emit()
        else:
            self.rotated_ccw.emit()
        self.last_steps = current

    def _on_button_press(self):
        """ボタンが押されたら発火"""
        self.button_pressed.emit()

    def stop(self):
        if self.rotor:
            self.rotor.close()
        if self.button:
            self.button.close()
