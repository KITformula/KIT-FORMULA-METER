import logging
import os
import subprocess

import can

from src.can.can_listeners import DashInfoListener, UdpPayloadListener
from src.can.mock_can_sender import MockCanSender
from src.fuel.fuel_calculator import FuelCalculator # fuel_calculator を受け取るために必要
from src.util import config # config.py から設定を読み込むために必要


class CanMaster:
    bus: can.BusABC
    dashInfoListener: DashInfoListener
    udpPayloadListener: UdpPayloadListener
    notifier: can.Notifier # notifier も型ヒントに追加

    # __init__ が fuel_calculator を受け取るように修正
    def __init__(self, fuel_calculator: FuelCalculator) -> None:
        
        # 1. CANバス（bus）のセットアップ
        # config.debug は config.py からインポートした debug 変数を参照
        if config.debug:
            logging.info("CAN master running in DEBUG mode (virtual bus)")
            mockCanSender = MockCanSender()
            mockCanSender.start()
            self.bus = can.Bus(channel="debug", interface="virtual")
        else:
            logging.info("CAN master running in PROD mode (socketcan)")
            r = subprocess.run("sudo ip link set can0 down", shell=True)
            if r.returncode == 0:
                logging.info("CAN interface can0 down succeeded!")
            else:
                logging.error("CAN interface can0 down failed!")
            r = subprocess.run(
                "sudo ip link set can0 type can bitrate 1000000", shell=True
            )
            if r.returncode == 0:
                logging.info("CAN interface can0 setting succeeded!")
            else:
                logging.error("CAN interface can0 setting failed!")
            r = subprocess.run("sudo ip link set can0 up", shell=True)
            if r.returncode == 0:
                logging.info("CAN interface can0 up succeeded!")
            else:
                logging.error("CAN interface can0 up failed!")
            self.bus = can.Bus(channel="can0", interface="socketcan")

        self.dashInfoListener = DashInfoListener(fuel_calculator)
        self.udpPayloadListener = UdpPayloadListener()

        # 3. Notifier（受付係）に、作成済みのリスナーを渡す
        self.notifier = can.Notifier(
            self.bus, [self.dashInfoListener, self.udpPayloadListener]
        )
    def __del__(self) -> None:
        # notifier と bus が確実に存在する場合のみ終了処理を行う
        if hasattr(self, "notifier"):
            self.notifier.stop()
        if hasattr(self, "bus"):
            self.bus.shutdown()

    # 外部（Application）への公式窓口
    dashMachineInfo = property(lambda self: self.dashInfoListener.dashMachineInfo)