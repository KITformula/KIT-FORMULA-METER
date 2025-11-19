from abc import ABC, abstractmethod
from src.models.models import DashMachineInfo

class TelemetrySender(ABC):
    """
    テレメトリ送信の抽象基底クラス (Interface)
    DIP: Applicationはこの抽象に依存する
    """

    @abstractmethod
    def start(self) -> None:
        """送信処理の開始（接続やスレッド起動など）"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """送信処理の停止（切断やスレッド停止など）"""
        pass

    @abstractmethod
    def send(self, info: DashMachineInfo, fuel_percent: float, tpms_data: dict) -> None:
        """
        車両データを送信する
        SRP: データの変換と送信の責任を持つ
        """
        pass