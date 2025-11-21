from src.can.can_master import CanMaster

# from src.message.message import Messenger
# from src.udp.udp_transmitter import UdpTransmitter
from src.fuel.fuel_calculator import FuelCalculator


class MachineException(BaseException):
    pass


class Machine:
    machineId: int

    canMaster: CanMaster
    # udpTransmitter: UdpTransmitter
    # messenger: Messenger

    def __init__(self, fuel_calculator: FuelCalculator) -> None:
        # ★★★ 3. 受け取った fuel_calculator を CanMaster に渡す ★★★
        self.canMaster = CanMaster(fuel_calculator)
        # self.messenger = Messenger()

    def initialise(self) -> None:
        # self.udpTransmitter = UdpTransmitter(self.canMaster.udpPayloadListener)
        # self.udpTransmitter.start()
        # self.messenger.start()
        pass
