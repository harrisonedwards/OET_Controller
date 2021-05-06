import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from function_generator import FunctionGenerator
from pump import Pump
from nikon_control_wrapper import Microscope
from fluorescence_controller import FluorescenceController
from camera import Camera
from PyQt5.QtCore import QThread


class ImageViewer(QtWidgets.QWidget):
    resize_event_signal = QtCore.pyqtSignal(QtCore.QSize)

    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.image = QtGui.QImage()
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.image)
        self.image = QtGui.QImage()

    @QtCore.pyqtSlot(QtGui.QImage)
    def setImage(self, image):
        self.image = image
        self.update()

    def sizeHint(self):
        return QtCore.QSize(2060//3, 2048//3)

    def heightForWidth(self, width):
        return width * 2048//2060

    def resizeEvent(self, event):
        print('imviewer resized')
        self.resize_event_signal.emit(self.size())


class Window(QtWidgets.QWidget):
    start_video_signal = QtCore.pyqtSignal()


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
        self.dispenseMode = None



        # self.changeOETPatternPushbutton = QtWidgets.QPushButton(text='Change OET Pattern')
        # self.changeOETPatternPushbutton.clicked.connect(self.changeOETPattern)

        # MICROSCOPE
        # TODO: query all of these positions and set them correctly initially
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
        self.frequencyDoubleSpinBox.setMaximum(100000000)
        self.waveformComboBox = QtWidgets.QComboBox()
        self.waveformComboBox.addItems(['SIN', 'SQU'])
        self.fgOutputCombobox = QtWidgets.QComboBox()
        self.fgOutputCombobox.addItems(['OFF', 'ON'])
        self.fgOutputCombobox.currentTextChanged.connect(self.changeFunctionGeneratorOutput)
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
        self.pumpAmountRadioButton = QtWidgets.QRadioButton()
        self.pumpAmountRadioButton.clicked.connect(self.startAmountDispenseMode)
        self.pumpAmountDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.pumpAmountDoubleSpinBox.setSuffix('ul')
        self.pumpAmountDoubleSpinBox.setMaximum(10000)
        self.pumpAmountDoubleSpinBox.setFixedWidth(80)

        self.pumpTimeLabel = QtWidgets.QLabel(text='Time')
        self.pumpTimeRadioButton = QtWidgets.QRadioButton()
        self.pumpTimeRadioButton.clicked.connect(self.startTimeDispenseMode)
        # self.pumpTimeRadioButton.
        self.pumpTimeDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.pumpTimeDoubleSpinBox.setSuffix('min')
        self.pumpTimeDoubleSpinBox.setMaximum(30 * 60)
        self.pumpTimeDoubleSpinBox.setSingleStep(0.01)
        self.pumpTimeRadioButton.click()

        self.pumpDispensePushButton = QtWidgets.QPushButton(text='Dispense')
        self.pumpDispensePushButton.clicked.connect(self.pumpDispense)
        self.pumpWithdrawPushButton = QtWidgets.QPushButton(text='Withdraw')
        self.pumpWithdrawPushButton.clicked.connect(self.pumpWithdraw)
        self.pumpStopPushButton = QtWidgets.QPushButton(text='Halt')
        self.pumpStopPushButton.clicked.connect(self.pumpStop)

        # arrange the widgets
        self.VBoxLayout = QtWidgets.QVBoxLayout(self)

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
        self.functionGeneratorLayout.addWidget(self.waveformComboBox)
        self.functionGeneratorLayout.addWidget(self.setFunctionGeneratorPushButton)
        self.functionGeneratorLayout.addWidget(self.fgOutputCombobox)
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
        self.pumpLayout.addWidget(self.pumpAmountRadioButton)
        self.pumpLayout.addWidget(self.pumpAmountLabel)
        self.pumpLayout.addWidget(self.pumpAmountDoubleSpinBox)
        self.pumpLayout.addWidget(self.pumpTimeRadioButton)
        self.pumpLayout.addWidget(self.pumpTimeLabel)
        self.pumpLayout.addWidget(self.pumpTimeDoubleSpinBox)
        self.pumpLayout.addWidget(self.pumpDispensePushButton)
        self.pumpLayout.addWidget(self.pumpWithdrawPushButton)
        self.pumpLayout.addWidget(self.pumpStopPushButton)
        self.HBoxLayout.addWidget(self.pumpGroupBox)
        if not self.pump:
            self.pumpGroupBox.setEnabled(False)

        # self.HBoxLayout.addWidget(self.changeOETPatternPushbutton)

        self.image_viewer = ImageViewer()

        self.camera = Camera()
        self.camera_thread = QThread()
        self.camera_thread.start()
        self.camera.moveToThread(self.camera_thread)
        self.camera.VideoSignal.connect(self.image_viewer.setImage)

        self.image_viewer.resize_event_signal.connect(self.camera.resize_slot)

        # self.VBoxLayout.setAlignment(QtCore.Qt.AlignBottom)
        self.image_viewer.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self.VBoxLayout.addWidget(self.image_viewer)

        self.VBoxLayout.addLayout(self.HBoxLayout)

        # self.showMaximized()
        # connect to the video thread and start the video
        self.start_video_signal.connect(self.camera.startVideo)
        self.start_video_signal.emit()



    def startAmountDispenseMode(self):
        self.dispenseMode = 'amount'
        self.pumpTimeDoubleSpinBox.setEnabled(False)
        self.pumpAmountDoubleSpinBox.setEnabled(True)

    def startTimeDispenseMode(self):
        self.dispenseMode = 'time'
        self.pumpAmountDoubleSpinBox.setEnabled(False)
        self.pumpTimeDoubleSpinBox.setEnabled(True)

    def pumpDispense(self):
        rate = self.pumpSpeedDoubleSpinBox.value()
        if self.dispenseMode == 'amount':
            amt = self.pumpAmountDoubleSpinBox.value()
        elif self.dispenseMode == 'time':
            amt = self.pumpTimeDoubleSpinBox.value() * rate
        self.pump.dispense(amt, rate)

    def pumpWithdraw(self):
        rate = self.pumpSpeedDoubleSpinBox.value()
        if self.dispenseMode == 'amount':
            amt = self.pumpAmountDoubleSpinBox.value()
        elif self.dispenseMode == 'time':
            amt = self.pumpTimeDoubleSpinBox.value() * rate
        self.pump.withdraw(amt, rate)

    def pumpStop(self):
        self.pump.halt()

    def changeFunctionGeneratorOutput(self, text):
        self.fg.change_output(text)

    def setFunctionGenerator(self):
        v = self.voltageDoubleSpinBox.value()
        f = self.frequencyDoubleSpinBox.value()
        w = self.waveformComboBox.currentText()
        self.fg.set_voltage(v)
        self.fg.set_frequency(f)
        self.fg.set_waveform(w)

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
    window.activateWindow()
    sys.exit(app.exec_())
