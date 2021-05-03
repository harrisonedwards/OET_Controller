import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from function_generator import FunctionGenerator
from pump import Pump
from nikon_control_wrapper import Microscope
from fluorescenceController import FluorescenceController


class cameraFeed(QtWidgets.QGraphicsView):
    photoClicked = QtCore.pyqtSignal(QtCore.QPoint)
    photoReleased = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self):
        super(cameraFeed, self).__init__()
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))


class Window(QtWidgets.QWidget):
    def __init__(self):
        super(Window, self).__init__()

        try:
            self.fg = FunctionGenerator()
        except Exception as e:
            print(f'Function generator control not available: {e}')
            self.fg = False

        try:
            self.pump = Pump()
        except Exception as e:
            print(f'Pump control not available: {e}')
            self.pump = False

        try:
            self.fc = FluorescenceController()
        except Exception as e:
            print(f'Fluorescence control not available: {e}')
            self.fc = False

        try:
            self.microscope = Microscope()
        except Exception as e:
            print(f'Microscope control not available: {e}')
            self.microscope = False

        self.setWindowTitle('OET System Control')

        # make all of our different widgets
        # self.cameraFeed = cameraFeed()
        # self.changeOETPatternPushbutton = QtWidgets.QPushButton(text='Change OET Pattern')
        # self.changeOETPatternPushbutton.clicked.connect(self.changeOETPattern)

        # MICROSCOPE
        self.filter_positions = ['DAPI', 'GFP', 'Red', 'Brightfield', 'PE-Cy7', 'empty']
        self.objectives = ['2x', '4x', '10x', '20x', '40x', 'empty']
        self.magnificationLabel = QtWidgets.QLabel(text='Magnification:')
        self.magnificationComboBoxWidget = QtWidgets.QComboBox()
        self.magnificationComboBoxWidget.addItems(self.objectives)
        self.magnificationComboBoxWidget.currentTextChanged.connect(self.changeMagnification)
        self.zAxisLabel = QtWidgets.QLabel(text='Z:')
        self.zAxisPositionDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.zAxisPositionDoubleSpinBox.valueChanged.connect(self.setZAxisPosition)
        self.filterLabel = QtWidgets.QLabel(text='Filter:')
        self.filterComboBoxWidget = QtWidgets.QComboBox()
        self.filterComboBoxWidget.addItems(self.filter_positions)
        self.filterComboBoxWidget.currentTextChanged.connect(self.changeFilter)

        # FUNCTION GENERATOR
        self.voltageLabel = QtWidgets.QLabel(text='Voltage:')
        self.voltageDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.voltageDoubleSpinBox.setMaximum(10)
        self.voltageDoubleSpinBox.setMinimum(-10)
        self.voltageDoubleSpinBox.setSuffix('V')
        self.frequencyLabel = QtWidgets.QLabel(text='Frequency:')
        self.frequencyDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.frequencyDoubleSpinBox.setDecimals(0)
        self.frequencyDoubleSpinBox.setSingleStep(100)
        self.frequencyDoubleSpinBox.setSuffix('Hz')
        self.frequencyDoubleSpinBox.setFixedWidth(80)
        self.frequencyDoubleSpinBox.setMaximum(100000)
        self.setFunctionGeneratorPushButton = QtWidgets.QPushButton('Set')
        self.setFunctionGeneratorPushButton.clicked.connect(self.setFunctionGenerator)

        # FLUORESCENCE CONTROLLER
        self.fluorescenceIntensityLabel = QtWidgets.QLabel(text='Intensity')
        self.fluorescenceIntensityDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.fluorescenceIntensityDoubleSpinBox.valueChanged.connect(self.changeFluorescenceIntensity)
        self.fluorescenceIntensityDoubleSpinBox.setSuffix('%')
        self.fluorescenceIntensityDoubleSpinBox.setMaximum(100)
        self.fluorescenceShutterLabel = QtWidgets.QLabel('Shutter:')
        self.fluorescenceShutterCheckBox = QtWidgets.QCheckBox()
        self.fluorescenceShutterCheckBox.clicked.connect(self.changeShutter)

        # PUMP
        self.pumpSpeedLabel = QtWidgets.QLabel(text='Rate')
        self.pumpSpeedDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.pumpSpeedDoubleSpinBox.setSuffix('ul/min')
        self.pumpSpeedDoubleSpinBox.setMaximum(10000)
        self.pumpSpeedDoubleSpinBox.setFixedWidth(100)
        self.pumpAmountLabel = QtWidgets.QLabel(text='Amount')
        self.pumpAmountDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.pumpAmountDoubleSpinBox.setSuffix('ul')
        self.pumpAmountDoubleSpinBox.setMaximum(10000)
        self.pumpAmountDoubleSpinBox.setFixedWidth(80)
        self.pumpDispensePushButton = QtWidgets.QPushButton(text='Dispense')
        self.pumpDispensePushButton.clicked.connect(self.pumpDispense)
        self.pumpWithdrawPushButton = QtWidgets.QPushButton(text='Withdraw')
        self.pumpWithdrawPushButton.clicked.connect(self.pumpWithdraw)
        self.pumpStopPushButton = QtWidgets.QPushButton(text='Halt')
        self.pumpStopPushButton.clicked.connect(self.pumpStop)

        # arrange the widgets
        self.VBoxLayout = QtWidgets.QVBoxLayout(self)
        # self.VBoxLayout.addWidget(self.cameraFeed)

        self.HBoxLayout = QtWidgets.QHBoxLayout()
        self.HBoxLayout.setAlignment(QtCore.Qt.AlignCenter)

        self.microscopeGroupBox = QtWidgets.QGroupBox('Microscope')
        self.microscopeLayout = QtWidgets.QHBoxLayout()
        self.microscopeGroupBox.setLayout(self.microscopeLayout)
        self.microscopeLayout.addWidget(self.magnificationLabel)
        self.microscopeLayout.addWidget(self.magnificationComboBoxWidget)
        self.microscopeLayout.addWidget(self.filterLabel)
        self.microscopeLayout.addWidget(self.filterComboBoxWidget)
        self.microscopeLayout.addWidget(self.zAxisLabel)
        self.microscopeLayout.addWidget(self.zAxisPositionDoubleSpinBox)
        self.HBoxLayout.addWidget(self.microscopeGroupBox)
        if not self.microscope:
            self.microscopeGroupBox.setEnabled(False)

        self.functionGeneratorGroupBox = QtWidgets.QGroupBox('Function Generator')
        self.functionGeneratorLayout = QtWidgets.QHBoxLayout()
        self.functionGeneratorGroupBox.setLayout(self.functionGeneratorLayout)
        self.functionGeneratorLayout.addWidget(self.voltageLabel)
        self.functionGeneratorLayout.addWidget(self.voltageDoubleSpinBox)
        self.functionGeneratorLayout.addWidget(self.frequencyLabel)
        self.functionGeneratorLayout.addWidget(self.frequencyDoubleSpinBox)
        self.functionGeneratorLayout.addWidget(self.setFunctionGeneratorPushButton)
        self.HBoxLayout.addWidget(self.functionGeneratorGroupBox)
        if not self.fg:
            self.functionGeneratorGroupBox.setEnabled(False)

        self.fluorescenceGroupBox = QtWidgets.QGroupBox('Fluorescence')
        self.fluorescenceLayout = QtWidgets.QHBoxLayout()
        self.fluorescenceGroupBox.setLayout(self.fluorescenceLayout)
        self.fluorescenceLayout.addWidget(self.fluorescenceShutterLabel)
        self.fluorescenceLayout.addWidget(self.fluorescenceShutterCheckBox)
        self.fluorescenceLayout.addWidget(self.fluorescenceIntensityLabel)
        self.fluorescenceLayout.addWidget(self.fluorescenceIntensityDoubleSpinBox)
        self.HBoxLayout.addWidget(self.fluorescenceGroupBox)
        if not self.fc:
            self.fluorescenceGroupBox.setEnabled(False)

        self.pumpGroupBox = QtWidgets.QGroupBox('Pump')
        self.pumpLayout = QtWidgets.QHBoxLayout()
        self.pumpGroupBox.setLayout(self.pumpLayout)
        self.pumpLayout.addWidget(self.pumpSpeedLabel)
        self.pumpLayout.addWidget(self.pumpSpeedDoubleSpinBox)
        self.pumpLayout.addWidget(self.pumpAmountLabel)
        self.pumpLayout.addWidget(self.pumpAmountDoubleSpinBox)
        self.pumpLayout.addWidget(self.pumpDispensePushButton)
        self.pumpLayout.addWidget(self.pumpWithdrawPushButton)
        self.pumpLayout.addWidget(self.pumpStopPushButton)
        self.HBoxLayout.addWidget(self.pumpGroupBox)
        if not self.pump:
            self.pumpGroupBox.setEnabled(False)

        # self.HBoxLayout.addWidget(self.changeOETPatternPushbutton)

        self.VBoxLayout.addLayout(self.HBoxLayout)

    def setFunctionGenerator(self):
        v = self.voltageDoubleSpinBox.value()
        f = self.frequencyDoubleSpinBox.value()
        self.fg.set_voltage(v)
        self.fg.set_frequency(f)

    def pumpStop(self):
        self.pump.halt()

    def pumpDispense(self):
        amt = self.pumpAmountDoubleSpinBox.value()
        rate = self.pumpSpeedDoubleSpinBox.value()
        self.pump.dispense(amt, rate)

    def pumpWithdraw(self):
        amt = self.pumpAmountDoubleSpinBox.value()
        rate = self.pumpSpeedDoubleSpinBox.value()
        self.pump.withdraw(amt, rate)

    def changeOETPattern(self):
        pass

    def changeFluorescenceIntensity(self, value):
        self.fc.change_intensity(value)

    def changeMagnification(self, text):
        idx_dict = {k: v for k, v in zip(self.objectives, range(1, 7))}
        self.microscope.set_objective(idx_dict[text])

    def changeFilter(self, text):
        idx_dict = {k: v for k, v in zip(self.filter_positions, range(1, 7))}
        self.microscope.set_filter(idx_dict[text])

    def setZAxisPosition(self, value):
        self.microscope.set_z(value)

    def changeShutter(self):
        state = self.fluorescenceShutterCheckBox.checkState()
        self.microscope.set_shutter(state)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    # window.setGeometry(500, 300, 800, 600)
    window.show()
    sys.exit(app.exec_())
