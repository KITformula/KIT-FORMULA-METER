from PyQt5.QtCore import QObject, pyqtSignal
from gpiozero import RotaryEncoder
import logging

logger = logging.getLogger(__name__)

class EncoderWorker(QObject):
    """
    gpiozeroのロータリーエンコーダ入力をPyQtのシグナルに変換するクラス
    """
    # GUIスレッドに通知するためのシグナル
    rotated_cw = pyqtSignal()   # 時計回り (Clockwise)
    rotated_ccw = pyqtSignal()  # 反時計回り (Counter-Clockwise)
    button_pressed = pyqtSignal() # スイッチ押し込み (必要であれば)

    def __init__(self, pin_a=27, pin_b=17, parent=None):
        super().__init__(parent)
        self.rotor = None
        try:
            # max_steps=0 で制限なし回転モード
            # wrap=True にすると値がループしますが、ここでは方向だけ検知したいので単純化します
            self.rotor = RotaryEncoder(a=pin_a, b=pin_b, max_steps=0)
            self.rotor.when_rotated = self._on_rotate
            self.last_steps = 0
            logger.info(f"Encoder initialized on pins A={pin_a}, B={pin_b}")
        except Exception as e:
            logger.error(f"Failed to initialize RotaryEncoder (Simulation Mode?): {e}")

    def _on_rotate(self):
        """バックグラウンドスレッドから呼ばれるコールバック"""
        if self.rotor is None:
            return
            
        current_steps = self.rotor.steps
        # 値が増えていれば時計回り、減っていれば反時計回り
        # (配線によっては逆になるので、実機で逆なら emit を入れ替えてください)
        if current_steps > self.last_steps:
            self.rotated_cw.emit()
        else:
            self.rotated_ccw.emit()
        
        self.last_steps = current_steps

    def stop(self):
        if self.rotor:
            self.rotor.close()