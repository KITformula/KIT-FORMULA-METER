import datetime

from PyQt5 import QtCore
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QProgressBar,
    QSizePolicy,
)

from src.models.models import (
    BatteryVoltage,
    GearType,
    Message,
    OilPress,
    OilPressStatus,
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
        self.setFlat(True)
        self.layout = QGridLayout()
        self.setObjectName("TitleValueBox")
        self.setStyleSheet(
            "QGroupBox#TitleValueBox { border: 2px solid #ffffff; border-radius: 3px;}"
        )
        self.TitleFont = "Arial"
        self.titleColor = "#FD6"
        self.valueFont = "Arial"
        self.valueColor = "#FFF"
        self.titleBackgroundColor = "#000"

        self.titleLabel = QCustomLabel()
        self.titleLabel.setText(titleLabel)
        # self.titleLabel.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)
        self.titleLabel.setFontFamily(self.TitleFont)
        self.titleLabel.setFontScale(0.55)
        self.titleLabel.setStyleSheet(
            "color :"
            + self.titleColor
            + "; background-color:"
            + self.titleBackgroundColor
            + ";font-weight: bold"
        )

        self.valueLabel = QCustomLabel()
        self.valueLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.valueLabel.setFontFamily(self.valueFont)
        self.valueLabel.setFontScale(0.75)
        self.valueLabel.setStyleSheet(
            "font-weight: bold; color :" + self.valueColor + ";"
        )
        # self.setStyleSheet("color : #FFF; background-color: #000;")

        self.layout.addWidget(self.titleLabel, 0, 0)
        self.layout.addWidget(self.valueLabel, 1, 0)
        self.layout.setRowStretch(0, 1)
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

    # --------------- update background warning color  ----------
    def updateWaterTempWarning(self, waterTemp: WaterTemp):
        if waterTemp.status == WaterTempStatus.LOW:
            color = "#000"
        elif waterTemp.status == WaterTempStatus.MIDDLE:
            color = "#FB0"
        elif waterTemp.status == WaterTempStatus.HIGH:
            color = "#F00"
        self.valueLabel.setStyleSheet(
            "font-weight: bold; border-radius: 5px; color: #FFF; background-color:"
            + color
            + ";"
        )

    def updateOilTempWarning(self, oilTemp: OilTemp):
        if oilTemp.status == OilTempStatus.LOW:
            color = "#000"
        elif oilTemp.status == OilTempStatus.MIDDLE:
            color = "#FB0"
        elif oilTemp.status == OilTempStatus.HIGH:
            color = "#F00"
        self.valueLabel.setStyleSheet(
            "font-weight: bold; border-radius: 5px; color: #FFF; background-color:"
            + color
            + ";"
        )

    def updateOilPressWarning(self, oilPress: OilPress):
        # self.valueLabel.setText(str(round(oilPress, 2)))
        if oilPress.status == OilPressStatus.LOW:
            color = "#F00"
        elif oilPress.status == OilPressStatus.MIDDLE:
            color = "#FB0"
        elif oilPress.status == OilPressStatus.HIGH:
            color = "#000"
        self.valueLabel.setStyleSheet(
            "font-weight: bold; border-radius: 5px; color: #FFF; background-color:"
            + color
            + ";"
        )

    def updateFanWarning(self, fanEnable: bool):
        if fanEnable:
            color = "#000"
        else:
            color = "#F00"
        self.valueLabel.setStyleSheet(
            "font-weight: bold; border-radius: 5px; color: #FFF; background-color:"
            + color
            + ";"
        )


class IconValueBox(QGroupBox):
    def __init__(self, iconPath=None):
        super(IconValueBox, self).__init__(None)
        self.setFlat(True)

        self.valueFont = QFont("Monospaced Font", 18)
        self.valueColor = "#FFF"
        self.layout = QGridLayout()

        # ★★★★★ ここに移動します ★★★★★
        # if文の前にvalueLabelの作成と設定を移動させることで、
        # アイコンの有無に関わらず、必ず作成されるようにします。
        self.valueLabel = QCustomLabel()
        self.valueLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.valueLabel.setFontScale(0.6)
        self.valueLabel.setFontFamily("Arial")
        self.valueLabel.setStyleSheet("QLabel { color : " + self.valueColor + "; }")
        # ★★★★★ ここまで ★★★★★

        # iconPathが指定されている（Noneではない）場合
        if iconPath:
            self.iconLabel = QLabel(self)
            self.iconLabel.setPixmap(QPixmap(iconPath))
            self.iconLabel.setAlignment(QtCore.Qt.AlignCenter)
            
            self.layout.addWidget(self.iconLabel, 0, 0)
            self.layout.addWidget(self.valueLabel, 0, 1) # valueLabelは既に作成済み
            self.layout.setColumnStretch(0, 1)
            self.layout.setColumnStretch(1, 3)
        # iconPathが指定されていない（Noneの）場合
        else:
            # アイコンラベルは作成せず、valueLabelが全幅を使う
            self.layout.addWidget(self.valueLabel, 0, 0, 1, 2) # valueLabelは既に作成済み

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
      
    def updateBatteryValueLabel(self, batteryVoltage: BatteryVoltage):
        """
        電圧値を受け取り、テキストの表示と色の警告を一度に行う
        """
       # "BAT " の後ろに半角スペースを入れる
        display_text = f"BAT {batteryVoltage:.1f} V"

        # --- 2. 色の決定 ---
        # 次に、渡された電圧値に基づいて使用する色を決定します
        color_to_set = "#48BB78"  # デフォルトは緑色

        if batteryVoltage < 13.0:
            color_to_set = "#E53E3E"   # 13.0未満は赤
        elif batteryVoltage <= 13.4:
            color_to_set = "#ECC94B"  # 13.0以上13.1以下は黄
    
        # --- 3. スタイル（色）とテキストを適用 ---
        # 決定した色で、valueLabelの文字色（color）を更新します
        # 注意: フォント設定なども含めて再指定しないと、スタイルがリセットされる可能性があります
        font_style = "font: bold 35pt 'Arial';" # 例としてフォントも再指定
        self.valueLabel.setStyleSheet(f"color: {color_to_set}; {font_style}")
        
        # 最後に、整形したテキストをラベルに設定します
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
        # self.adjustSize()
        # self.setMaximum(Rpm.MAX)
        self.setMaximum(maxValue)
        # self.setValue(40)
        self.setTextVisible(False)
        self.setOrientation(QtCore.Qt.Horizontal)
        # self.setStyleSheet(
        #     """
        #     QProgressBar
        #         {
        #             border: 2px solid;
        #             border-color: #AAA;
        #             border-radius: 5px;
        #             background-color: #333;
        #         }
        #     """
        # )
        self.setStyleSheet(
            """
            QProgressBar
                {
                    border: 2px solid;
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
        self.setFlat(True)
        self.setStyleSheet("border:0;")

        self.layout = QGridLayout()

        # # shift point 8500
        # self.lightRpm_1 = 1000
        # self.lightRpm_2 = 2000
        # self.lightRpm_3 = 3000
        # self.lightRpm_4 = 4000
        # self.lightRpm_5 = 4500
        # self.lightRpm_6 = 5000
        # self.lightRpm_7 = 5500
        # self.lightRpm_8 = 6000
        # self.lightRpm_9 = 6500
        # self.lightRpm_10 = 7000
        # self.lightRpm_11 = 7500
        # self.lightRpm_12 = 8000

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


        # self.layout.setContentsMargins(0, 0, 0, 0)
        # self.layout.setSpacing(0)

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
        self.setFlat(True)
        self.setStyleSheet("border:0;")
        # self.setFixedSize(51, 40)

        self.offColor = "#333"  # dark gray
        self.shiftRpm = 12300
        self.shiftColor = "#ffff00"  # yellow

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
        self.setFontFamily("Monospaced Font")
        self.setFontScale(3.0)
        self.setStyleSheet("color : #FFF; background-color: #000")

    def updateGearLabel(self, gearType: GearType):
        if int(gearType) == GearType.NEUTRAL:
            self.setText("N")
            self.setStyleSheet("font-weight: bold; color : #00ff7f;")
        else:
            self.setText(str(int(gearType)))
            self.setStyleSheet("font-weight: bold; color : #FFF;")


class RpmLabel(QCustomLabel):
    def __init__(self):
        super(RpmLabel, self).__init__()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFontFamily("Monospaced Font")
        self.setFontScale(0.8)
        self.setStyleSheet("font-weight: bold; color : #FFF; background-color: #000")

    def updateRpmLabel(self, rpm: Rpm):
        self.setText(str(rpm))


class LapCountLabel(QCustomLabel):
    def __init__(self):
        super(LapCountLabel, self).__init__()

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFontFamily("Monospaced Font")
        self.setFontScale(0.8)
        self.setStyleSheet("color : #ffffff; background-color: #000")

    def updateLapCountLabel(self, message: Message):

        self.setText(str(round(message.laptime, 1))+"0.00")
