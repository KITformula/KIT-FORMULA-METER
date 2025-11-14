import sys
from PyQt5.QtWidgets import QApplication
# QTimer をインポート
from PyQt5.QtCore import QTimer,pyqtSlot,QObject

from src.machine.machine import Machine
from src.gui.gui import MainWindow, WindowListener
from src.fuel.fuel_calculator import FuelCalculator
from src.gui.splash_screen import SplashScreen 
from src.util import config
from src.util.fuel_store import FuelStore
from src.tpms.tpms_worker import TpmsWorker


class Application(QObject,WindowListener):

    def __init__(self):
        super().__init__()
        
        # --- 1. 燃料保存ストレージを準備 ---
        self.fuel_store = FuelStore()
        
        # --- 2. 起動時の残量をロード ---
        
        # configの満タン値（タンク容量）を取得
        tank_capacity_ml = config.INITIAL_FUEL_ML
        
        # ロードを試み、失敗(None)したら config の値を使う (初回起動対応)
        current_start_ml = self.fuel_store.load_state() or tank_capacity_ml
            
        self.fuel_calculator = FuelCalculator(
            injector_flow_rate_cc_per_min=config.INJECTOR_FLOW_RATE_CC_PER_MIN,
            num_cylinders=config.NUM_CYLINDERS,
            tank_capacity_ml=tank_capacity_ml,
            current_remaining_ml=current_start_ml
        )
        
        self.machine = Machine(self.fuel_calculator)


        self.tpms_worker = TpmsWorker(
            frequency=config.RTL433_FREQUENCY,
            id_map=config.TPMS_ID_MAP,
            debug_mode=config.debug,
        )
        # TPMSの最新データを保持する辞書
        self.latest_tpms_data = {}
        

        self.app: QApplication = None
        self.splash: SplashScreen = None
        self.window: MainWindow = None

        self.fuel_save_timer = QTimer()


    def initialize(self) -> None:
        self.app = QApplication(sys.argv)
        screen_size = self.app.primaryScreen().size()
        image_path = "src/gui/icons/kitformula2.png"

        # --- スプラッシュスクリーンの準備 ---
        self.splash = SplashScreen(image_path, screen_size)
        self.tpms_worker.data_updated.connect(self.on_tpms_update)
        
        self.splash.ready_for_heavy_init.connect(self.perform_initialization)
        self.splash.fade_out_finished.connect(self.show_main_window)
        self.splash.start()

        # --- アプリ終了時に最終保存を行うシグナルを接続 ---
        self.app.aboutToQuit.connect(self.save_fuel_state)
        self.app.aboutToQuit.connect(self.tpms_worker.stop)

        sys.exit(self.app.exec_())


    def perform_initialization(self):
        """
        (スロット) 実際の初期化処理とフェードアウトの開始
        """
        self.machine.initialise()
        self.window = MainWindow(self)
        # --- 燃料の定期保存タイマーを起動 ---
        self.fuel_save_timer.timeout.connect(self.save_fuel_state)
        # (修正) config から読み込んだ値を使う
        self.fuel_save_timer.start(config.FUEL_SAVE_INTERVAL_MS)
        self.tpms_worker.start()

        self.splash.start_fade_out()
    
    # --- (新設) TPMSデータ受信時のスロット ---
    @pyqtSlot(dict)
    def on_tpms_update(self, data: dict):
        """TPMSワーカーからデータを受け取り、最新の状態を更新する"""
        # 辞書をマージ (例: {"FL": ...} と {"FR": ...} を { "FL": ..., "FR": ...} に)
        self.latest_tpms_data.update(data)
        # print(f"TPMSデータ更新: {self.latest_tpms_data}") # (デバッグ用)

    def show_main_window(self):
        """(スロット) フェードアウト完了後、メインウィンドウを表示"""
        if self.window:
            self.window.showFullScreen()
            self.app.processEvents()
        
        if self.splash:
            self.splash.close()
            self.splash = None 

        
    def onUpdate(self) -> None:
        
        dash_info = self.machine.canMaster.dashMachineInfo
        fuel_percentage = self.fuel_calculator.remaining_fuel_percent
        
        if self.window is not None:
            self.window.updateDashboard(
                dash_info, 
                fuel_percentage,
                self.latest_tpms_data, 
                #self.machine.messenger.message
            )
        return super().onUpdate()

    # --- 燃料保存を実行するメソッド ---
    def save_fuel_state(self):
        """
        現在の燃料残量（RAM上）を NVM (fuel_store) に保存する。
        (タイマーとアプリ終了時に呼ばれる)
        """
        current_ml = self.fuel_calculator.remaining_fuel_ml
        self.fuel_store.save_state(current_ml)