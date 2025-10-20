import sys
from PyQt5.QtWidgets import (
    QApplication, 
    QWidget, 
    QLabel, 
    QVBoxLayout, 
    QGraphicsOpacityEffect
)
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer

from src.machine.machine import Machine
from src.gui.gui import MainWindow, WindowListener
from src.fuel.fuel_calculator import FuelCalculator




class Application(WindowListener):

    def __init__(self):
        super().__init__()
        INJECTOR_FLOW_RATE: float = 186.8  # インジェクターの噴射量 (cc/min)
        NUM_CYLINDERS: int = 4                       # エンジンの気筒数
        self.fuel_calculator = FuelCalculator(INJECTOR_FLOW_RATE, NUM_CYLINDERS)
        self.machine = Machine(self.fuel_calculator)

    def initialize(self) -> None:
        self.app = QApplication(sys.argv)
        screen_size = self.app.primaryScreen().size()

        # --- ロゴ画像の準備 ---
        image_path = "src/gui/icons/kitformula2.png"
        logo_pixmap = QPixmap(image_path)
        
        if logo_pixmap.isNull():
            print(f"エラー: 画像ファイルの読み込みに失敗しました！パスを確認してください: {image_path}")
            return
        
        # 画面サイズに合わせてロゴをスケーリング
        scaled_logo = logo_pixmap.scaled(screen_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


        # 1. 背景用の黒いQWidgetを作成
        self.splash_container = QWidget()
        self.splash_container.setStyleSheet("background-color: black;")
        # スプラッシュスクリーンとして振る舞うためのフラグを設定
        self.splash_container.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 2. ロゴ表示用のQLabelを作成
        self.logo_label = QLabel(self.splash_container)
        self.logo_label.setPixmap(scaled_logo)
        self.logo_label.setAlignment(Qt.AlignCenter)

        # 3. レイアウトを使ってQLabelを中央に配置
        layout = QVBoxLayout(self.splash_container)
        layout.addWidget(self.logo_label)
        self.splash_container.setLayout(layout)

        # 4. ロゴラベルに透明度エフェクトを設定
        self.opacity_effect = QGraphicsOpacityEffect(self.logo_label)
        self.logo_label.setGraphicsEffect(self.opacity_effect)
        
        # 最初はロゴを完全に透明にする
        self.opacity_effect.setOpacity(0)

        # --- アニメーションの設定 ---
        # フェードインアニメーション (対象: 透明度エフェクト)
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(1500) # 1.5秒かけて表示
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.finished.connect(self.start_main_initialization)

        # フェードアウトアニメーション (対象: 透明度エフェクト)
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(2500) # 2.5秒かけて消す
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.finished.connect(self.show_main_window)
        
        # スプラッシュコンテナを表示し、アニメーションを開始
        self.splash_container.showFullScreen()
        self.fade_in.start()

        sys.exit(self.app.exec_())

    def start_main_initialization(self):
        """フェードイン完了後、重い初期化処理を実行"""
        # GUIが固まるのを防ぐため、初期化処理を少し遅延させて実行
        QTimer.singleShot(100, self.perform_initialization)

    def perform_initialization(self):
        """実際の初期化処理とフェードアウトの開始"""
        self.machine.initialise()
        self.window = MainWindow(self)
        # 初期化が終わったらフェードアウトを開始
        self.fade_out.start()

    def show_main_window(self):
        """フェードアウト完了後、メインウィンドウを表示"""
        self.window.showFullScreen()
        self.app.processEvents()
        self.splash_container.close()

        
    def onUpdate(self) -> None:
         # a. 最新のCANデータを取得
        dash_info = self.machine.canMaster.dashMachineInfo
        
        # c. 計算結果（パーセンテージ）を取得する
        fuel_percentage = self.fuel_calculator.remaining_fuel_percent
        
        # d. GUIに全ての最新データを渡す
        if hasattr(self, "window"):
            self.window.updateDashboard(
                dash_info, 
                fuel_percentage, # ★★★ 計算結果を渡す
                self.machine.messenger.message
            )
        return super().onUpdate()
