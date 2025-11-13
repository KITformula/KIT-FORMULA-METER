import sys
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect, QApplication
from PyQt5.QtGui import QPixmap
# QTimer をインポート
from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtSignal, QTimer

class SplashScreen(QWidget):
    """
    ロゴの表示とフェードイン・フェードアウトアニメーションを管理する
    スプラッシュスクリーン用ウィジェット。
    """
    
    # --- シグナル定義 ---
    
    # 重い初期化処理を開始する準備ができたことを通知するシグナル
    # (フェードイン完了 + 100ms遅延後)
    ready_for_heavy_init = pyqtSignal()
    
    # フェードアウトアニメーション完了時に発行されるシグナル
    fade_out_finished = pyqtSignal()

    def __init__(self, image_path: str, screen_size):
        """
        Args:
            image_path (str): 表示するロゴ画像のパス
            screen_size: QApplicationから取得したプライマリ画面のサイズ
        """
        super().__init__()
        
        # メンバー変数の初期化
        self.logo_label = None
        self.opacity_effect = None
        self.fade_in = None
        self.fade_out = None
        
        logo_pixmap = QPixmap(image_path)
        
        if logo_pixmap.isNull():
            print(f"エラー: 画像ファイルの読み込みに失敗しました！パスを確認してください: {image_path}")
            return # logo_label は None のまま

        # 画面サイズに合わせてロゴをスケーリング
        scaled_logo = logo_pixmap.scaled(screen_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # 1. 背景用の黒いQWidget（自分自身）の設定
        self.setStyleSheet("background-color: black;")
        # スプラッシュスクリーンとして振る舞うためのフラグを設定
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 2. ロゴ表示用のQLabelを作成
        self.logo_label = QLabel(self)
        self.logo_label.setPixmap(scaled_logo)
        self.logo_label.setAlignment(Qt.AlignCenter)

        # 3. レイアウトを使ってQLabelを中央に配置
        layout = QVBoxLayout(self)
        layout.addWidget(self.logo_label)
        self.setLayout(layout)

        # 4. ロゴラベルに透明度エフェクトを設定
        self.opacity_effect = QGraphicsOpacityEffect(self.logo_label)
        self.logo_label.setGraphicsEffect(self.opacity_effect)
        
        # 最初はロゴを完全に透明にする
        self.opacity_effect.setOpacity(0)

        # --- アニメーションの設定 ---
        # フェードインアニメーション
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(1500) # 1.5秒かけて表示
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        # 完了したら内部メソッド _on_fade_in_finished を呼ぶ
        self.fade_in.finished.connect(self._on_fade_in_finished) 

        # フェードアウトアニメーション
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(2500) # 2.5秒かけて消す
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        # 完了したらシグナルを発行
        self.fade_out.finished.connect(self.fade_out_finished.emit)

    def start(self):
        """スプラッシュスクリーンの表示とフェードインを開始"""
        if self.logo_label is None:
             print("エラー: スプラッシュは正しく初期化されていません（ロゴなし）。")
             # ロゴがない場合は、即座に初期化シグナルを発行してフォールバックさせる
             self._on_fade_in_finished()
             return

        if self.opacity_effect.opacity() == 0: # 初期状態か確認
            self.showFullScreen()
            self.fade_in.start()
        else:
            print("エラー: スプラッシュはすでに開始されているか、不正な状態です。")

    def start_fade_out(self):
        """フェードアウトを開始"""
        if self.fade_out:
            # 現在の透明度から開始するように設定（念のため）
            current_opacity = self.opacity_effect.opacity()
            self.fade_out.setStartValue(current_opacity)
            self.fade_out.start()
        else:
             print("エラー: フェードアウトアニメーションが初期化されていません。")
             self.fade_out_finished.emit() # 即座に終了シグナルを出す

    def _on_fade_in_finished(self):
        """
        (内部メソッド) フェードイン完了時に呼び出される。
        GUIが固まるのを防ぐため、100ms遅延させてから
        ready_for_heavy_init シグナルを発行する。
        """
        QTimer.singleShot(100, self.ready_for_heavy_init.emit)