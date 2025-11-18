import sys
import time
import threading
import random  # ★ 擬似データ用にインポート
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, pyqtSlot, QObject

from src.machine.machine import Machine
from src.gui.gui import MainWindow, WindowListener
from src.fuel.fuel_calculator import FuelCalculator
from src.gui.splash_screen import SplashScreen
from src.util import config
from src.util.fuel_store import FuelStore
from src.tpms.tpms_worker import TpmsWorker

# ★ デバッグモードでない場合のみ、GpsWorkerをインポート
if not config.debug:
    from src.gps.gps_worker import GpsWorker, calculate_distance_meters
else:
    # デバッグモード時は、型ヒントのためだけにダミーのクラスを定義 (中身は不要)
    class GpsWorker: pass
    def calculate_distance_meters(a,b,c,d): return 0


class Application(QObject, WindowListener):

    def __init__(self):
        super().__init__()

        # --- 1. 燃料・マシン設定 ---
        self.fuel_store = FuelStore()
        tank_capacity_ml = config.INITIAL_FUEL_ML
        current_start_ml = self.fuel_store.load_state() or tank_capacity_ml

        self.fuel_calculator = FuelCalculator(
            injector_flow_rate_cc_per_min=config.INJECTOR_FLOW_RATE_CC_PER_MIN,
            num_cylinders=config.NUM_CYLINDERS,
            tank_capacity_ml=tank_capacity_ml,
            current_remaining_ml=current_start_ml
        )
        self.machine = Machine(self.fuel_calculator)

        # --- 2. TPMS Worker ---
        self.tpms_worker = TpmsWorker(
            frequency=config.RTL433_FREQUENCY,
            id_map=config.TPMS_ID_MAP,
            debug_mode=config.debug,
        )
        self.latest_tpms_data = {}

        # --- 3. GPS Worker (本番 or モック) ---
        self.gps_worker: GpsWorker | None = None
        self.gps_thread: threading.Thread | None = None
        
        # 状態保持用 (本番/モック共通)
        self.lap_count = 0
        self.previous_lap_time = 0.0
        
        if config.debug:
            # --- デバッグモード (モック用) ---
            print("★ GPSワーカーはモックモードで起動します ★")
            # 50msタイマーで加算する用の変数
            self.mock_lap_time_elapsed = 0.0 
            # 擬似ラップタイム (例: 10秒周期)
            self.mock_lap_duration = 10.0 
            self.mock_best_lap = 60.0 # 基準タイム
        else:
            # --- 本番モード (実機用) ---
            print("★ GPSワーカーは本番モードで起動します ★")
            self.gps_port = getattr(config, "GPS_PORT", "COM6")
            self.gps_baud = getattr(config, "GPS_BAUD", 115200)
            self.gps_worker = GpsWorker(self.gps_port, self.gps_baud)
            
            # 本番用のラップ計測変数
            self.lap_target_coords = None  # (lat, lon)
            self.last_lap_time = time.monotonic() # 基準時刻
            self.is_outside_lap_zone = True
            self.current_gps_data = {}

        # --- 4. Qtオブジェクト ---
        self.app: QApplication = None
        self.splash: SplashScreen = None
        self.window: MainWindow = None
        self.fuel_save_timer = QTimer()

    def initialize(self) -> None:
        self.app = QApplication(sys.argv)
        screen_size = self.app.primaryScreen().size()
        image_path = "src/gui/icons/kitformula2.png"

        self.splash = SplashScreen(image_path, screen_size)
        
        # --- シグナル接続 ---
        self.tpms_worker.data_updated.connect(self.on_tpms_update)
        
        # ★ 本番モードの場合のみ、GPSワーカーのシグナルを接続
        if not config.debug and self.gps_worker:
            self.gps_worker.data_received.connect(self.on_gps_update)
            self.gps_worker.error_occurred.connect(
                lambda err: print(f"GPS Error: {err}")
            )

        self.splash.ready_for_heavy_init.connect(self.perform_initialization)
        self.splash.fade_out_finished.connect(self.show_main_window)
        self.splash.start()

        # --- アプリ終了シグナル ---
        self.app.aboutToQuit.connect(self.save_fuel_state)
        self.app.aboutToQuit.connect(self.tpms_worker.stop)
        if not config.debug and self.gps_worker:
            self.app.aboutToQuit.connect(self.gps_worker.stop) # ★

        sys.exit(self.app.exec_())

    def perform_initialization(self):
        """(スロット) 実際の初期化処理とフェードアウトの開始"""
        
        self.machine.initialise()
        self.window = MainWindow(self)
        
        # ★ GUIからのスタートライン設定シグナルを接続 (本番時のみ意味がある)
        self.window.requestSetStartLine.connect(self.set_start_line)

        self.fuel_save_timer.timeout.connect(self.save_fuel_state)
        self.fuel_save_timer.start(config.FUEL_SAVE_INTERVAL_MS)
        
        # --- ワーカーの起動 ---
        self.tpms_worker.start()

        # ★ 本番モードの場合のみ、GPSワーカーをスレッドで起動
        if not config.debug and self.gps_worker:
            self.gps_thread = threading.Thread(target=self.gps_worker.run, daemon=True)
            self.gps_thread.start()

        self.splash.start_fade_out()

    @pyqtSlot(dict)
    def on_tpms_update(self, data: dict):
        """TPMSワーカーからデータを受け取り、最新の状態を更新する"""
        self.latest_tpms_data.update(data)

    @pyqtSlot(dict)
    def on_gps_update(self, data: dict):
        """(本番用) GPSワーカーからデータを受け取り、ラップ判定を実行する"""
        if config.debug: return # 万が一呼ばれても無視

        self.current_gps_data = data
        if hasattr(self.machine.canMaster.dashMachineInfo, 'gpsQuality'):
             self.machine.canMaster.dashMachineInfo.gpsQuality = data.get('quality', 0)
        self.check_lap_crossing(data)

    def show_main_window(self):
        """(スロット) フェードアウト完了後、メインウィンドウを表示"""
        if self.window:
            self.window.showFullScreen()
            self.app.processEvents()
        if self.splash:
            self.splash.close()
            self.splash = None

    def onUpdate(self) -> None:
        """GUIタイマーによって定期的に呼び出される (50ms周期)"""
        
        dash_info = self.machine.canMaster.dashMachineInfo
        fuel_percentage = self.fuel_calculator.remaining_fuel_percent

        # ★ モードに応じてラップタイムを更新
        if config.debug:
            # モックモード: 50ms加算して擬似ラップを生成
            self.update_mock_gps_lap(dash_info)
        else:
            # 本番モード: リアルタイムの経過時間を計算
            if hasattr(dash_info, 'currentLapTime') and self.last_lap_time:
                current_lap_duration = time.monotonic() - self.last_lap_time
                dash_info.currentLapTime = current_lap_duration

        # 共通のGUI更新
        if self.window is not None:
            self.window.updateDashboard(
                dash_info,
                fuel_percentage,
                self.latest_tpms_data,
            )
        return super().onUpdate()

    def save_fuel_state(self):
        """現在の燃料残量を NVM (fuel_store) に保存する"""
        current_ml = self.fuel_calculator.remaining_fuel_ml
        self.fuel_store.save_state(current_ml)

    # --- ★ モック用ラップタイム生成ロジック ---
    
    def update_mock_gps_lap(self, dash_info):
        """(デバッグ用) onUpdateタイマーで擬似ラップデータを生成する"""
        
        # 50ms (onUpdateの周期) ずつ加算
        self.mock_lap_time_elapsed += 0.050
        
        # 確定したラップタイムではなく、現在の経過時間を表示
        dash_info.currentLapTime = self.mock_lap_time_elapsed

        # 擬似ラップ周期 (例: 10秒) を超えたらラップを確定
        if self.mock_lap_time_elapsed >= self.mock_lap_duration:
            
            # --- 擬似ラップ確定 ---
            self.lap_count += 1
            dash_info.lapCount = self.lap_count
            
            # 基準タイム +/- 2秒 の範囲で擬似ラップタイムを生成
            lap_time = self.mock_lap_duration + random.uniform(-2.0, 2.0)
            
            if self.lap_count > 1:
                delta = lap_time - self.previous_lap_time
            else:
                delta = 0.0 # 1周目は差分なし
            
            dash_info.lapTimeDiff = delta
            
            # GUI上では確定したラップタイムを次の周まで表示
            dash_info.currentLapTime = lap_time
            
            # 次のラップの準備
            self.previous_lap_time = lap_time
            self.mock_lap_time_elapsed = 0.0 # タイマーリセット
            
            print(f"MOCK LAP {self.lap_count}: {lap_time:.2f}s (Diff: {delta:+.2f}s)")
            
            # 次のラップタイムを 基準 +/- 3秒 の範囲でランダムに設定
            self.mock_lap_duration = self.mock_best_lap + random.uniform(-3.0, 3.0)


    # --- ★ 本番用ラップタイム計測ロジック ---

    def check_lap_crossing(self, current_data: dict):
        """(本番用) GPSデータに基づき、ラップ地点の通過を判定する"""
        
        if self.lap_target_coords is None: return
        if config.debug: return # 安全装置

        lat = current_data.get('latitude', 0.0)
        lon = current_data.get('longitude', 0.0)
        quality = current_data.get('quality', 0)
        status = current_data.get('status', 'V')
        
        is_valid_fix = (quality > 0 or status == 'A') and (lat != 0.0 or lon != 0.0)
        if not is_valid_fix: return

        target_lat, target_lon = self.lap_target_coords
        distance = calculate_distance_meters(target_lat, target_lon, lat, lon)
        current_time = time.monotonic()
        
        # 判定距離 (config.py から読み込むのを推奨)
        lap_radius = getattr(config, "GPS_LAP_RADIUS_METERS", 5.0)
        lap_cooldown = getattr(config, "GPS_LAP_COOLDOWN_SEC", 10.0)

        if distance <= lap_radius:
            time_since_last_lap = current_time - self.last_lap_time
            
            if self.is_outside_lap_zone and (time_since_last_lap > lap_cooldown):
                
                info = self.machine.canMaster.dashMachineInfo

                if self.lap_count > 0:
                    info.lapTimeDiff = time_since_last_lap - self.previous_lap_time
                else:
                    info.lapTimeDiff = 0.0
                
                self.previous_lap_time = time_since_last_lap
                self.lap_count += 1
                info.lapCount = self.lap_count
                
                # 基準時刻をリセット
                self.last_lap_time = current_time
                self.is_outside_lap_zone = False # ゾーン内に入った
                
                print(f"LAP {self.lap_count}: {time_since_last_lap:.2f}s (Diff: {info.lapTimeDiff:+.2f}s)")
        
        else:
            self.is_outside_lap_zone = True # ゾーンの外に出た

    @pyqtSlot()
    def set_start_line(self):
        """(スロット) 現在地をスタートラインに設定"""
        
        # モックモード時は何もしない
        if config.debug:
            print("MOCK: スタートライン設定をスキップ (スペースキー無効)")
            # モックのラップカウントをリセットする
            self.lap_count = 0
            self.previous_lap_time = 0.0
            self.mock_lap_time_elapsed = 0.0
            if self.machine:
                info = self.machine.canMaster.dashMachineInfo
                info.lapCount = 0
                info.lapTimeDiff = 0.0
                info.currentLapTime = 0.0
            return

        # --- (本番モードのロジック) ---
        lat = self.current_gps_data.get('latitude', 0.0)
        lon = self.current_gps_data.get('longitude', 0.0)
        
        if lat != 0.0 and lon != 0.0:
            self.lap_target_coords = (lat, lon)
            self.lap_count = 0
            self.last_lap_time = time.monotonic()
            self.previous_lap_time = 0.0
            
            info = self.machine.canMaster.dashMachineInfo
            info.lapCount = 0
            info.lapTimeDiff = 0.0
            info.currentLapTime = 0.0
            
            print(f"★ スタートライン設定: {lat}, {lon}")
        else:
            print("★ GPS測位が無効なため、スタートラインを設定できません。")