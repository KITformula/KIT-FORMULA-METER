import datetime

from PyQt5 import QtCore
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QProgressBar,
    QSizePolicy,
)

from src.models.models import (
    BatteryVoltage,
    FuelPress,
    GearType,
    Message,
    # OilPress,
    # OilPressStatus,
    OilTemp,
    OilTempStatus,
    Rpm,
    WaterTemp,
    WaterTempStatus,
)


class QCustomLabel(QLabel):
    def __init__(self):
        super(QCustomLabel, self).__init__()
        self._font = QFont()
        # self.setFont(self._font)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._fontScale = 1.0

    def setFontFamily(self, face):
        self._font.setFamily(face)

    def setFontScale(self, scale):
        self._fontScale = scale

    def resizeEvent(self, evt):
        width = self.size().width() / 2
        height = self.size().height()
        baseSize = 0
        if width > height:
            baseSize = height
        else:
            baseSize = width

        self._font.setPixelSize(int(baseSize * self._fontScale))
        self.setFont(self._font)


class TitleValueBox(QGroupBox):
    def __init__(self, titleLabel):
        super(TitleValueBox, self).__init__(None)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setFlat(True)
        self.layout = QGridLayout()
        self.setObjectName("TitleValueBox")

        # ボックス自体の背景を黒に
        self.setStyleSheet(
            "QGroupBox#TitleValueBox { border: none; background-color: #000; border-radius: 0px; margin: 0px; }"
        )

        # ★修正: 写真のような太めのサンセリフ体（DejaVu Sans）に統一
        self.TitleFont = "DejaVu Sans"
        self.titleColor = "#FD6"
        self.valueFont = "DejaVu Sans"  # Monoを削除
        self.valueColor = "#FFF"
        self.titleBackgroundColor = "#000"

        self.titleLabel = QCustomLabel()
        self.titleLabel.setText(titleLabel)
        self.titleLabel.setFontFamily(self.TitleFont)
        self.titleLabel.setFontScale(0.55)
        # ラベル自体にも背景黒を指定して透過を防ぐ
        self.titleLabel.setStyleSheet(
            "color :"
            + self.titleColor
            + "; background-color:"
            + self.titleBackgroundColor
            + ";font-weight: bold;"
        )

        self.valueLabel = QCustomLabel()
        self.valueLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.valueLabel.setFontFamily(self.valueFont)
        self.valueLabel.setFontScale(0.75)
        # ラベル自体にも背景黒を指定して透過を防ぐ
        self.valueLabel.setStyleSheet(
            "font-weight: bold; color :" + self.valueColor + "; background-color: #000;"
        )

        self.layout.addWidget(self.titleLabel, 0, 0)
        self.layout.addWidget(self.valueLabel, 1, 0)
        self.layout.setRowStretch(0, 0)
        self.layout.setRowStretch(1, 2)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.setLayout(self.layout)

    def updateValueLabel(self, value):
        self.valueLabel.setText(str(value))

    def updateBoolValueLabel(self, value: bool):
        if value:
            self.valueLabel.setText("ON")
        else:
            self.valueLabel.setText("OFF")

    def updateTempValueLabel(self, waterTemp: WaterTemp):
        """
        WaterTempオブジェクトを受け取り、数値を表示する専用メソッド
        """
        if hasattr(waterTemp, "value"):
            display_text = f"{waterTemp.value:.0f}"
        else:
            display_text = f"{int(waterTemp):.0f}"

        self.valueLabel.setText(display_text)

    # --------------- update background warning color  ----------
    def updateWaterTempWarning(self, waterTemp: WaterTemp):
        if waterTemp.status == WaterTempStatus.LOW:
            color = "#00bfff"
        elif waterTemp.status == WaterTempStatus.MIDDLE:
            color = "#000000"
        elif waterTemp.status == WaterTempStatus.WARNING:
            color = "#FB0"
        elif waterTemp.status == WaterTempStatus.HIGH:
            color = "#F00"

        # 背景色が変わる場合でも、他のスタイル（配置など）を維持する
        self.valueLabel.setStyleSheet(
            f"font-weight: bold; border-radius: 5px; color: #FFF; qproperty-alignment: 'AlignCenter'; background-color: {color};"
        )

    def updateOilTempWarning(self, oilTemp: OilTemp):
        if oilTemp.status == OilTempStatus.LOW:
            color = "#000"
        elif oilTemp.status == OilTempStatus.MIDDLE:
            color = "#FB0"
        elif oilTemp.status == OilTempStatus.HIGH:
            color = "#F00"

        self.valueLabel.setStyleSheet(
            f"font-weight: bold; border-radius: 5px; color: #FFF; qproperty-alignment: 'AlignCenter'; background-color: {color};"
        )

    def updateFanWarning(self, fanEnable: bool):
        if fanEnable:
            color = "#000"
        else:
            color = "#F00"

        self.valueLabel.setStyleSheet(
            f"font-weight: bold; border-radius: 5px; color: #FFF; background-color: {color};"
        )


# ★★★ 追加: デルタタイム専用の表示ボックス (SOLID原則: 単一責任の原則) ★★★
class DeltaBox(TitleValueBox):
    """
    ラップタイムの差分（デルタ）を表示するための専用ウィジェット。
    GUIクラスから色分けロジックを分離し、自身の表示責任を持つ。
    """

    def __init__(self, titleLabel="Delta"):
        super(DeltaBox, self).__init__(titleLabel)

    def updateDelta(self, diff: float):
        """
        差分値を受け取り、フォーマットと色を更新する
        Args:
            diff (float): ラップタイム差分 (秒)
        """
        # 1. 符号付きでフォーマット (+0.00, -0.00)
        self.valueLabel.setText(f"{diff:+.2f}")

        # 2. 値に応じた色の決定
        if diff < 0:
            # マイナス（速い） -> 緑
            color = "#0F0"
        elif diff > 0:
            # プラス（遅い） -> 赤
            color = "#F00"
        else:
            # ゼロ -> 白
            color = "#FFF"

        # 3. スタイルの適用 (背景黒を維持)
        self.valueLabel.setStyleSheet(
            f"font-weight: bold; color: {color}; background-color: #000;"
        )


class IconValueBox(QGroupBox):
    def __init__(self, iconPath=None):
        super(IconValueBox, self).__init__(None)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setFlat(True)

        # ★修正: 写真のような太めのサンセリフ体（DejaVu Sans）に統一
        self.valueFont = QFont("DejaVu Sans", 18, QFont.Bold)  # Monoを削除
        self.valueColor = "#FFF"
        self.layout = QGridLayout()

        self.setObjectName("IconValueBox")
        self.setStyleSheet(
            "QGroupBox#IconValueBox { border: none; background-color: #000; margin: 0px; }"
        )

        self.valueLabel = QCustomLabel()
        self.valueLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.valueLabel.setFontScale(0.75)
        self.valueLabel.setFontFamily("DejaVu Sans")  # Monoを削除
        # ここでも背景黒を明示
        self.valueLabel.setStyleSheet(
            "QLabel { color : "
            + self.valueColor
            + "; background-color: #000; font-weight: bold; }"
        )

        if iconPath:
            self.iconLabel = QLabel(self)
            self.iconLabel.setPixmap(QPixmap(iconPath))
            self.iconLabel.setAlignment(QtCore.Qt.AlignCenter)
            self.iconLabel.setStyleSheet("background-color: #000;")  # アイコン背景も黒

            self.layout.addWidget(self.iconLabel, 0, 0)
            self.layout.addWidget(self.valueLabel, 0, 1)
            self.layout.setColumnStretch(0, 1)
            self.layout.setColumnStretch(1, 3)
        else:
            self.layout.addWidget(self.valueLabel, 0, 0, 1, 2)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

    def updateBatteryValueLabel(self, batteryVoltage: BatteryVoltage):
        display_text = f" {batteryVoltage:.1f} V"
        color_to_set = "#7fff00"

        if batteryVoltage < 13.0:
            color_to_set = "#E53E3E"
        elif batteryVoltage <= 13.4:
            color_to_set = "#ECC94B"

        self.valueLabel.setStyleSheet(
            f"font-weight: bold; color: {color_to_set}; background-color: #000;"
        )
        self.valueLabel.setText(display_text)

    def updateFuelPressValueLabel(self, fuelPress: FuelPress):
        display_text = f"{fuelPress:.1f} kPa"
        new_color = "#7fff00"

        if fuelPress < 28.0:
            new_color = "#E53E3E"
        else:
            new_color = "#7fff00"
        self.valueLabel.setStyleSheet(
            f"font-weight: bold; color: {new_color}; background-color: #000;"
        )
        self.valueLabel.setText(display_text)

    def updateFuelPercentLabel(self, fuel_percentage: float):
        # ★修正: floatの小数点以下を表示せず、intに変換して整数表示にする
        display_text = f"{int(fuel_percentage)} %"
        new_color = "#7fff00"

        if fuel_percentage < 20.0:
            new_color = "#E53E3E"
        elif fuel_percentage < 50.0:
            new_color = "#ECC94B"
        else:
            new_color = "#7fff00"

        self.valueLabel.setStyleSheet(
            f"font-weight: bold; color: {new_color}; qproperty-alignment: 'AlignCenter'; background-color: #000;"
        )
        self.valueLabel.setText(display_text)

    def updateMessageLabel(self, message: Message):
        self.valueLabel.setText(message.text)

    def updateTime(self):
        dt_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        self.valueLabel.setText(dt_now.strftime("%H:%M"))


class PedalBar(QProgressBar):
    def __init__(self, barColor, maxValue):
        super(PedalBar, self).__init__(None)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMaximum(maxValue)
        self.setTextVisible(False)
        self.setOrientation(QtCore.Qt.Horizontal)

        self.setStyleSheet(
            """
            QProgressBar
                {
                    border: 1px solid;
                    border-color: #ffffff;
                    border-radius: 5px;
                    background-color: #333;
                }
            QProgressBar::chunk
                {
                    background-color: %s;
                    
                }
            """
            % (barColor)
        )

    def updatePedalBar(self, value):
        self.setValue(int(value))


class RpmLightBar(QGroupBox):
    def __init__(self):
        super(RpmLightBar, self).__init__(None)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setFlat(True)
        self.setStyleSheet("border:0; background-color: #000;")

        self.layout = QGridLayout()

        # shift point 9000
        self.lightRpm_1 = 1000
        self.lightRpm_2 = 2000
        self.lightRpm_3 = 3000
        self.lightRpm_4 = 4000
        self.lightRpm_5 = 5000
        self.lightRpm_6 = 5500
        self.lightRpm_7 = 6000
        self.lightRpm_8 = 7900
        self.lightRpm_9 = 8000
        self.lightRpm_10 = 9000
        self.lightRpm_11 = 10000
        self.lightRpm_12 = 10500
        self.lightRpm_13 = 11000
        self.lightRpm_14 = 11500
        self.lightRpm_15 = 12000

        self.greenLightColor = "#0F0"
        self.BlueLightColor = "#00ffff"
        self.redLightColor = "#F00"
        self.blueLightColor = "#8FF"

        self.light_1 = RpmLight(self.lightRpm_1, self.greenLightColor)
        self.light_2 = RpmLight(self.lightRpm_2, self.greenLightColor)
        self.light_3 = RpmLight(self.lightRpm_3, self.greenLightColor)
        self.light_4 = RpmLight(self.lightRpm_4, self.greenLightColor)
        self.light_5 = RpmLight(self.lightRpm_5, self.greenLightColor)
        self.light_6 = RpmLight(self.lightRpm_6, self.redLightColor)
        self.light_7 = RpmLight(self.lightRpm_7, self.redLightColor)
        self.light_8 = RpmLight(self.lightRpm_8, self.redLightColor)
        self.light_9 = RpmLight(self.lightRpm_9, self.redLightColor)
        self.light_10 = RpmLight(self.lightRpm_10, self.redLightColor)
        self.light_11 = RpmLight(self.lightRpm_11, self.BlueLightColor)
        self.light_12 = RpmLight(self.lightRpm_12, self.BlueLightColor)
        self.light_13 = RpmLight(self.lightRpm_13, self.BlueLightColor)
        self.light_14 = RpmLight(self.lightRpm_14, self.BlueLightColor)
        self.light_15 = RpmLight(self.lightRpm_15, self.BlueLightColor)

        self.layout.addWidget(self.light_1, 0, 0)
        self.layout.addWidget(self.light_2, 0, 1)
        self.layout.addWidget(self.light_3, 0, 2)
        self.layout.addWidget(self.light_4, 0, 3)
        self.layout.addWidget(self.light_5, 0, 4)
        self.layout.addWidget(self.light_6, 0, 5)
        self.layout.addWidget(self.light_7, 0, 6)
        self.layout.addWidget(self.light_8, 0, 7)
        self.layout.addWidget(self.light_9, 0, 8)
        self.layout.addWidget(self.light_10, 0, 9)
        self.layout.addWidget(self.light_11, 0, 10)
        self.layout.addWidget(self.light_12, 0, 11)
        self.layout.addWidget(self.light_13, 0, 12)
        self.layout.addWidget(self.light_14, 0, 13)
        self.layout.addWidget(self.light_15, 0, 14)

        self.setLayout(self.layout)

    def updateRpmBar(self, rpm: Rpm):
        self.light_1.updateRpmLightColor(rpm)
        self.light_2.updateRpmLightColor(rpm)
        self.light_3.updateRpmLightColor(rpm)
        self.light_4.updateRpmLightColor(rpm)
        self.light_5.updateRpmLightColor(rpm)
        self.light_6.updateRpmLightColor(rpm)
        self.light_7.updateRpmLightColor(rpm)
        self.light_8.updateRpmLightColor(rpm)
        self.light_9.updateRpmLightColor(rpm)
        self.light_10.updateRpmLightColor(rpm)
        self.light_11.updateRpmLightColor(rpm)
        self.light_12.updateRpmLightColor(rpm)
        self.light_13.updateRpmLightColor(rpm)
        self.light_14.updateRpmLightColor(rpm)
        self.light_15.updateRpmLightColor(rpm)


class RpmLight(QGroupBox):
    def __init__(self, onRpm, onColor):
        super(RpmLight, self).__init__(None)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setFlat(True)
        self.setStyleSheet("border:0;")

        self.offColor = "#333"  # dark gray
        self.shiftRpm = 12300
        self.shiftColor = "#ffff00"

        self.onRpm = onRpm
        self.onColor = onColor

    def updateRpmLightColor(self, rpm: Rpm):
        if rpm < self.onRpm:
            color = self.offColor
        elif rpm < self.shiftRpm:
            color = self.onColor
        else:
            color = self.shiftColor
        self.setStyleSheet("background-color: " + color + ";")


class GearLabel(QCustomLabel):
    def __init__(self):
        super(GearLabel, self).__init__()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFontFamily("DejaVu Sans")  # ★修正: 太字ゴシック
        self.setFontScale(2.5)
        self.setStyleSheet("color : #FFF; background-color: #000; font-weight: bold;")

    def updateGearLabel(self, gearType: GearType):
        if int(gearType) == GearType.NEUTRAL:
            self.setText("N")
            self.setStyleSheet(
                "font-weight: bold; color : #00ff7f; background-color: #000;"
            )
        else:
            self.setText(str(int(gearType)))
            self.setStyleSheet(
                "font-weight: bold; color : #FFF; background-color: #000;"
            )


class RpmLabel(QCustomLabel):
    def __init__(self):
        super(RpmLabel, self).__init__()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFontFamily("DejaVu Sans")  # ★修正: 太字ゴシック
        self.setFontScale(0.8)
        self.setStyleSheet("font-weight: bold; color : #FFF; background-color: #000")

    def updateRpmLabel(self, rpm: Rpm):
        self.setText(str(rpm))


class LapTimerLabel(QCustomLabel):
    def __init__(self):
        super(LapTimerLabel, self).__init__()

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFontFamily("DejaVu Sans")  # ★修正: 太字ゴシック
        self.setFontScale(0.8)
        self.setStyleSheet("color : #ffffff; background-color: #000")

    def updateLapTimerLabel(self, message: Message):
        self.setText(str(round(message.laptime, 1)) + "0.00")


class TpmsBox(QGroupBox):
    """
    一つのタイヤのTPMS（気温・気圧）を表示する
    カスタムウィジェット（1マス分）
    """

    def __init__(self, title: str):
        super(TpmsBox, self).__init__(title)

        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        # ★修正: 写真のような太めのサンセリフ体（DejaVu Sans）に統一
        self.temp_style_base = (
            "font-family: 'DejaVu Sans'; font-size: 70px; font-weight: bold;"
        )
        self.pressure_style_base = (
            "font-family: 'DejaVu Sans'; font-size: 20px; font-weight: bold;"
        )

        self.color_ok = "color: #FFF;"
        self.color_no_data = "color: #888;"

        self.setObjectName("TpmsBox")
        self.setStyleSheet(
            "QGroupBox#TpmsBox { border: none; background-color: #000; margin: 0px; }"
        )

        # 1. 気温表示用のラベル (背景黒を追加)
        self.tempLabel = QLabel("---")
        self.tempLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.tempLabel.setStyleSheet(
            f"{self.temp_style_base} {self.color_no_data} background-color: #000;"
        )

        # 2. 気圧表示用のラベル (背景黒を追加)
        self.pressureLabel = QLabel("---")
        self.pressureLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.pressureLabel.setStyleSheet(
            f"{self.pressure_style_base} {self.color_no_data} background-color: #000;"
        )

        # 3. 真ん中の横線
        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)
        self.line.setStyleSheet("background-color: #555;")

        layout = QGridLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        layout.addWidget(self.tempLabel, 0, 0)
        layout.addWidget(self.line, 1, 0)
        layout.addWidget(self.pressureLabel, 2, 0)

        layout.setRowStretch(0, 3)
        layout.setRowStretch(1, 0)
        layout.setRowStretch(2, 1)

        self.setLayout(layout)

    def updateTemperature(self, temp_c: float | None):
        """気温ラベルを更新する"""
        if temp_c is None:
            self.tempLabel.setText("---")
            self.tempLabel.setStyleSheet(
                f"{self.temp_style_base} {self.color_no_data} background-color: #000;"
            )
        else:
            val = int(temp_c)
            self.tempLabel.setText(f"{val}")

            if val < 30:
                color = "#00BFFF"
            elif val < 40:
                color = "#FFFF00"
            elif val < 50:
                color = "#FFA500"
            else:
                color = "#FF0000"

            self.tempLabel.setStyleSheet(
                f"{self.temp_style_base} color: {color}; background-color: #000;"
            )

    def updatePressure(self, pressure_kpa: float | None):
        """気圧ラベルを更新する"""
        if pressure_kpa is None:
            self.pressureLabel.setText("---")
            self.pressureLabel.setStyleSheet(
                f"{self.pressure_style_base} {self.color_no_data} background-color: #000;"
            )
        else:
            self.pressureLabel.setText(f"{pressure_kpa:.0f} kPa")
            self.pressureLabel.setStyleSheet(
                f"{self.pressure_style_base} {self.color_ok} background-color: #000;"
            )
