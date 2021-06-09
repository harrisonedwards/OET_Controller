import sys

import PyQt5.QtGui
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from function_generator import FunctionGenerator
from pump import Pump
from microscope import Microscope
from fluorescence_controller import FluorescenceController
from camera import Camera
from stage import Stage
from PyQt5.QtCore import QThread
from mightex import Polygon1000
import cv2
import qimage2ndarray
import copy

class ImageViewer(QtWidgets.QWidget):
    resize_event_signal = QtCore.pyqtSignal(QtCore.QSize, 'PyQt_PyObject')
    click_event_signal = QtCore.pyqtSignal(QtGui.QMouseEvent)
    path_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.image = QtGui.QImage()
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
        self.ignore_release = True
        self.drawing = False
        self.robot_paths = []
        self.payload = {}
        self.begin_path = None

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        # draw in the center here
        x = int(self.width() / 2 - self.image.width() / 2)  # offset to draw in center
        print(self.width(), self.height(), self.image.width(), self.image.height())
        painter.drawImage(x, 0, self.image)
        self.image = QtGui.QImage()

    @QtCore.pyqtSlot('PyQt_PyObject')
    def setImage(self, image):
        qt_img = qimage2ndarray.array2qimage(image)
        # qt_img = QtGui.QImage(image.data, image.shape[1], image.shape[0], QtGui.QImage.Format_RGB888)
        self.image = qt_img
        self.update()

    def sizeHint(self):
        return QtCore.QSize(1536 // 2, 1024 // 2)

    def heightForWidth(self, width):
        return width * 1536 // 1024

    def resizeEvent(self, event):
        # force aspect ratio here
        h = self.height()
        w = int(1536 / 1024 * h)
        self.resize_event_signal.emit(QtCore.QSize(w, h), False)
        self.ignore_release = False

    def mouseReleaseEvent(self, event):
        # helper to ignore events if we are resizing
        if not self.ignore_release:
            h = self.height()
            w = int(1536 / 1024 * h)
            self.resize_event_signal.emit(QtCore.QSize(w, h), True)
            QtCore.QPoint()
        if self.drawing:
            self.payload['start_x'] = self.begin_path.x()
            self.payload['start_y'] = self.begin_path.y()
            self.payload['end_x'] = event.pos().x()
            self.payload['end_y'] = event.pos().y()
            print(f'payload: {self.payload}')
            self.path_signal.emit(copy.deepcopy(self.payload))

    def mousePressEvent(self, event):
        print(event.pos())
        self.ignore_release = True
        # self.click_event_signal.emit(event)
        if self.drawing:
            self.begin_path = event.pos()

    # def mouseMoveEvent(self, event):
    #     if event.buttons() and QtCore.Qt.LeftButton and self.drawing:


class Window(QtWidgets.QWidget):
    start_video_signal = QtCore.pyqtSignal()
    set_camera_expsure_signal = QtCore.pyqtSignal('PyQt_PyObject')
    set_camera_gain_signal = QtCore.pyqtSignal('PyQt_PyObject')
    screenshot_signal = QtCore.pyqtSignal()

    def __init__(self):
        super(Window, self).__init__()

        try:
            self.function_generator = FunctionGenerator()
        except Exception as e:
            print(f'Function generator control not available: {e}')
            self.function_generator = False

        try:
            self.pump = Pump()
        except Exception as e:
            print(f'Pump control not available: {e}')
            self.pump = False

        try:
            self.fluorescence_controller = FluorescenceController()
        except Exception as e:
            print(f'Fluorescence control not available: {e}')
            self.fluorescence_controller = False

        try:
            self.stage = Stage()
        except Exception as e:
            print(f'Stage not available: {e}')
            self.stage = False

        try:
            self.microscope = Microscope()
        except Exception as e:
            print(f'Microscope control not available: {e}')
            self.microscope = False

        try:
            self.dmd = Polygon1000(1140, 912)
        except Exception as e:
            print(f'unable to connect to polygon: {e}')
            self.dmd = False

        self.test_image = cv2.imread(r'C:\Users\Mohamed\Desktop\Harrison\5.png')
        self.setWindowTitle('OET System Control')
        self.dispenseMode = None

        self.takeScreenshotPushButton = QtWidgets.QPushButton(text='Screenshot')

        # MICROSCOPE
        # TODO: query all of these positions and set them correctly initially
        self.filter_positions = ['DAPI', 'GFP', 'Red', 'Brightfield', 'PE-Cy7', 'empty']
        self.objectives = ['2x', '4x', '10x', '20x', '40x', 'empty']
        self.magnificationLabel = QtWidgets.QLabel(text='Magnification:')
        self.magnificationComboBoxWidget = QtWidgets.QComboBox()
        self.magnificationComboBoxWidget.addItems(self.objectives)
        self.stageStepSizeLabel = QtWidgets.QLabel('XY Step Size:')
        self.xystageStepSizeDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.xystageStepSizeDoubleSpinBox.setSingleStep(1000)
        self.xystageStepSizeDoubleSpinBox.setMinimum(5000)
        self.xystageStepSizeDoubleSpinBox.setDecimals(0)
        self.xystageStepSizeDoubleSpinBox.setMaximum(100000)
        self.xystageStepSizeDoubleSpinBox.setValue(25000)
        self.zstageStepSizeLabel = QtWidgets.QLabel('Z Step Size:')
        self.zstageStepSizeDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.zstageStepSizeDoubleSpinBox.setSingleStep(1000)
        self.zstageStepSizeDoubleSpinBox.setMinimum(5000)
        self.zstageStepSizeDoubleSpinBox.setDecimals(0)
        self.zstageStepSizeDoubleSpinBox.setMaximum(50000)
        self.zstageStepSizeDoubleSpinBox.setValue(10000)
        self.filterLabel = QtWidgets.QLabel(text='Filter:')
        self.filterComboBoxWidget = QtWidgets.QComboBox()
        self.filterComboBoxWidget.addItems(self.filter_positions)

        self.diaPushButton = QtWidgets.QPushButton('DIA')
        self.diaPushButton.setCheckable(True)
        self.cameraExposureLabel = QtWidgets.QLabel('Exposure:')
        self.cameraExposureDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.cameraExposureDoubleSpinBox.setSuffix('ms')
        self.cameraExposureDoubleSpinBox.setMaximum(5000)
        self.cameraExposureDoubleSpinBox.setMinimum(30)
        self.cameraExposureDoubleSpinBox.setSingleStep(10)
        self.cameraExposureDoubleSpinBox.setValue(150)
        self.gainLabel = QtWidgets.QLabel('Gain:')
        self.gainDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.gainDoubleSpinBox.setMinimum(3.60)
        self.gainDoubleSpinBox.setSingleStep(5.0)
        self.gainDoubleSpinBox.setMaximum(50)
        self.cameraRotationPushButton = QtWidgets.QPushButton('Rotate')
        self.cameraRotationPushButton.setCheckable(True)

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
        self.waveformComboBox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.fgOutputCombobox = QtWidgets.QComboBox()
        self.fgOutputCombobox.addItems(['OFF', 'ON'])
        self.fgOutputCombobox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setFunctionGeneratorPushButton = QtWidgets.QPushButton('Set')

        # FLUORESCENCE CONTROLLER
        self.fluorescenceIntensityLabel = QtWidgets.QLabel(text='Intensity')
        self.fluorescenceIntensityDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.fluorescenceIntensityDoubleSpinBox.setSuffix('%')
        self.fluorescenceIntensityDoubleSpinBox.setMinimum(0)
        self.fluorescenceIntensityDoubleSpinBox.setMaximum(100)
        self.fluorescenceIntensityDoubleSpinBox.setSingleStep(5)
        self.fluorescenceShutterPushButton = QtWidgets.QPushButton('Shutter')
        self.fluorescenceShutterPushButton.setCheckable(True)

        # PUMP
        self.pumpSpeedLabel = QtWidgets.QLabel(text='Rate')
        self.pumpSpeedDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.pumpSpeedDoubleSpinBox.setSuffix('ul/min')
        self.pumpSpeedDoubleSpinBox.setMaximum(10000)
        self.pumpSpeedDoubleSpinBox.setFixedWidth(100)
        self.pumpAmountLabel = QtWidgets.QLabel(text='Amount')
        self.pumpAmountRadioButton = QtWidgets.QRadioButton()
        self.pumpAmountDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.pumpAmountDoubleSpinBox.setSuffix('ul')
        self.pumpAmountDoubleSpinBox.setMaximum(10000)
        self.pumpAmountDoubleSpinBox.setFixedWidth(80)
        self.pumpTimeLabel = QtWidgets.QLabel(text='Time')
        self.pumpTimeRadioButton = QtWidgets.QRadioButton()
        self.pumpTimeDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.pumpTimeDoubleSpinBox.setSuffix('min')
        self.pumpTimeDoubleSpinBox.setMaximum(30 * 60)
        self.pumpTimeDoubleSpinBox.setSingleStep(0.01)
        self.pumpDispensePushButton = QtWidgets.QPushButton(text='Dispense')
        self.pumpWithdrawPushButton = QtWidgets.QPushButton(text='Withdraw')
        self.pumpStopPushButton = QtWidgets.QPushButton(text='Halt')

        # DMD
        self.detectRobotsPushButton = QtWidgets.QPushButton('Detect Robots')
        self.drawPathsPushButton = QtWidgets.QPushButton('Draw Paths')
        self.drawPathsPushButton.setCheckable(True)
        self.oetMoveToPushButton = QtWidgets.QPushButton('Move To')
        self.oetActivatePushButton = QtWidgets.QPushButton('Activate')
        self.oetRunPushButton = QtWidgets.QPushButton('Run')
        self.oetSpeedLabel = QtWidgets.QLabel('Speed')
        self.oetSpeedDoubleSpinBox = QtWidgets.QDoubleSpinBox()

        # arrange the widgets
        self.VBoxLayout = QtWidgets.QVBoxLayout()

        self.HBoxLayout = QtWidgets.QHBoxLayout(self)

        self.microscopeGroupBox = QtWidgets.QGroupBox('Microscope')
        self.microscopeLayout = QtWidgets.QHBoxLayout()
        self.microscopeGroupBox.setLayout(self.microscopeLayout)
        # self.microscopeLayout.addWidget(self.magnificationLabel)
        # self.microscopeLayout.addWidget(self.magnificationComboBoxWidget)
        # self.microscopeLayout.addWidget(self.filterLabel)
        # self.microscopeLayout.addWidget(self.filterComboBoxWidget)
        # self.microscopeLayout.addWidget(self.stageStepSizeLabel)
        # self.microscopeLayout.addWidget(self.xystageStepSizeDoubleSpinBox)
        # self.microscopeLayout.addWidget(self.zstageStepSizeLabel)
        # self.microscopeLayout.addWidget(self.zstageStepSizeDoubleSpinBox)
        # self.microscopeLayout.addWidget(self.diaPushButton)
        self.microscopeLayout.addWidget(self.cameraExposureLabel)
        self.microscopeLayout.addWidget(self.cameraExposureDoubleSpinBox)
        self.microscopeLayout.addWidget(self.cameraRotationPushButton)
        self.microscopeLayout.addWidget(self.gainLabel)
        self.microscopeLayout.addWidget(self.gainDoubleSpinBox)
        self.microscopeLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.VBoxLayout.addWidget(self.microscopeGroupBox)
        # if not self.microscope:
        #     self.microscopeGroupBox.setEnabled(False)

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
        self.functionGeneratorLayout.setAlignment(QtCore.Qt.AlignLeft)
        # self.VBoxLayout.addWidget(self.functionGeneratorGroupBox)
        if not self.function_generator:
            self.functionGeneratorGroupBox.setEnabled(False)

        self.fluorescenceGroupBox = QtWidgets.QGroupBox('Fluorescence')
        self.fluorescenceLayout = QtWidgets.QHBoxLayout()
        self.fluorescenceGroupBox.setLayout(self.fluorescenceLayout)
        self.fluorescenceLayout.addWidget(self.fluorescenceShutterPushButton)
        self.fluorescenceLayout.addWidget(self.fluorescenceIntensityLabel)
        self.fluorescenceLayout.addWidget(self.fluorescenceIntensityDoubleSpinBox)
        self.fluorescenceLayout.setAlignment(QtCore.Qt.AlignLeft)
        # self.VBoxLayout.addWidget(self.fluorescenceGroupBox)
        if not self.fluorescence_controller:
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
        self.pumpLayout.setAlignment(QtCore.Qt.AlignLeft)
        # self.VBoxLayout.addWidget(self.pumpGroupBox)
        # if not self.pump:
        self.pumpGroupBox.setEnabled(False)

        self.oetGroupBox = QtWidgets.QGroupBox('OET Controls')
        self.oetLayout = QtWidgets.QHBoxLayout()
        self.oetGroupBox.setLayout(self.oetLayout)
        self.oetLayout.addWidget(self.detectRobotsPushButton)
        self.oetLayout.addWidget(self.drawPathsPushButton)
        self.oetLayout.addWidget(self.oetMoveToPushButton)
        self.oetLayout.addWidget(self.oetRunPushButton)
        self.oetLayout.addWidget(self.oetSpeedLabel)
        self.oetLayout.addWidget(self.oetSpeedDoubleSpinBox)
        self.oetLayout.setAlignment(QtCore.Qt.AlignLeft)
        if not self.dmd:
            self.oetGroupBox.setEnabled(False)

        self.VBoxLayout.addWidget(self.oetGroupBox)
        self.VBoxLayout.addWidget(self.takeScreenshotPushButton)

        self.image_viewer = ImageViewer()

        self.camera = Camera()
        self.camera_thread = QThread()
        self.camera_thread.start()

        self.image_viewer.resize_event_signal.connect(self.camera.resize_slot)
        self.image_viewer.path_signal.connect(self.camera.path_slot)
        self.set_camera_expsure_signal.connect(self.camera.set_exposure_slot)
        self.set_camera_gain_signal.connect(self.camera.set_gain_slot)

        self.camera.VideoSignal.connect(self.image_viewer.setImage)
        self.image_viewer.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.camera.moveToThread(self.camera_thread)

        self.image_viewer.click_event_signal.connect(self.handle_click)

        self.VBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        self.HBoxLayout.addLayout(self.VBoxLayout)
        self.HBoxLayout.addWidget(self.image_viewer)
        self.initialize_gui_state()
        # self.showMaximized()

        # connect to the video thread and start the video
        self.setChildrenFocusPolicy(QtCore.Qt.ClickFocus)


    def initialize_gui_state(self):
        # get the initial state and make the GUI synced to it
        # idx_dict = {k: v for k, v in zip(range(1, 7), self.objectives)}
        # objective = self.microscope.status.iNOSEPIECE
        # self.magnificationComboBoxWidget.setCurrentText(idx_dict[objective])
        #
        # idx_dict = {k: v for k, v in zip(range(1, 7), self.filter_positions)}
        # filter = self.microscope.status.iTURRET1POS
        # self.filterComboBoxWidget.setCurrentText(idx_dict[filter])
        #
        # fluor_shutter_state = self.microscope.status.iTURRET1SHUTTER
        # self.fluorescenceShutterPushButton.setChecked(fluor_shutter_state)
        #
        # dia_state = self.microscope.status.iSHUTTER_DIA
        # self.diaPushButton.setChecked(dia_state)

        # connect all of our control signals
        self.takeScreenshotPushButton.clicked.connect(self.camera.take_screenshot_slot)
        self.detectRobotsPushButton.clicked.connect(self.changeOETPattern)
        # self.magnificationComboBoxWidget.currentTextChanged.connect(self.changeMagnification)
        # self.xystageStepSizeDoubleSpinBox.valueChanged.connect(self.stage.set_xystep_size)
        # self.zstageStepSizeDoubleSpinBox.valueChanged.connect(self.microscope.set_zstep_size)
        # self.filterComboBoxWidget.currentTextChanged.connect(self.changeFilter)
        # self.diaPushButton.clicked.connect(self.toggleDia)
        self.cameraExposureDoubleSpinBox.valueChanged.connect(self.setCameraExposure)
        self.gainDoubleSpinBox.valueChanged.connect(self.setCameraGain)
        self.cameraRotationPushButton.clicked.connect(self.toggleRotation)
        self.detectRobotsPushButton.clicked.connect(self.detectRobots)
        self.drawPathsPushButton.clicked.connect(self.toggleDrawPaths)
        # if self.function_generator:
            # self.fgOutputCombobox.currentTextChanged.connect(self.function_generator.change_output)
        # self.setFunctionGeneratorPushButton.clicked.connect(self.setFunctionGenerator)
        # self.fluorescenceIntensityDoubleSpinBox.valueChanged.connect(self.fluorescence_controller.change_intensity)
        # self.fluorescenceShutterPushButton.clicked.connect(self.toggleFluorShutter)
        # self.pumpAmountRadioButton.clicked.connect(self.startAmountDispenseMode)
        # self.pumpTimeRadioButton.clicked.connect(self.startTimeDispenseMode)
        # self.pumpDispensePushButton.clicked.connect(self.pumpDispense)
        # self.pumpWithdrawPushButton.clicked.connect(self.pumpWithdraw)
        # self.pumpStopPushButton.clicked.connect(self.pump.halt)
        # self.pumpTimeRadioButton.click()
        # self.dmd.turn_on_led()

    def detectRobots(self):
        pass

    def toggleDrawPaths(self):
        state = self.drawPathsPushButton.isChecked()
        self.image_viewer.drawing = state


    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def handle_click(self, event):
        print(event.x(), event.y())


    def closeEvent(self, event):
        print('closing all connections...')
        for hardware in [self.microscope, self.fluorescence_controller, self.function_generator,
                         self.dmd, self.pump]:
            if hardware is not False:
                hardware.__del__()

    def setChildrenFocusPolicy(self, policy):
        def recursiveSetChildFocusPolicy(parentQWidget):
            for childQWidget in parentQWidget.findChildren(QtWidgets.QWidget):
                if isinstance(childQWidget, QtWidgets.QComboBox):
                    # make all comboboxes respond to nothing at all
                    childQWidget.setFocusPolicy(QtCore.Qt.NoFocus)
                else:
                    childQWidget.setFocusPolicy(policy)
                recursiveSetChildFocusPolicy(childQWidget)
        recursiveSetChildFocusPolicy(self)

    def keyPressEvent(self, event):
        key = event.key()
        if self.cameraRotationPushButton.isChecked():
            if key == QtCore.Qt.Key_Up:
                self.stage.step('r')
            elif key == QtCore.Qt.Key_Left:
                self.stage.step('u')
            elif key == QtCore.Qt.Key_Right:
                self.stage.step('d')
            elif key == QtCore.Qt.Key_Down:
                self.stage.step('l')
        else:
            if key == QtCore.Qt.Key_Up:
                self.stage.step('u')
            elif key == QtCore.Qt.Key_Left:
                self.stage.step('l')
            elif key == QtCore.Qt.Key_Right:
                self.stage.step('r')
            elif key == QtCore.Qt.Key_Down:
                self.stage.step('d')
        if key == QtCore.Qt.Key_PageUp:
            self.microscope.move_rel_z(self.zstageStepSizeDoubleSpinBox.value())
        elif key == QtCore.Qt.Key_PageDown:
            self.microscope.move_rel_z(-self.zstageStepSizeDoubleSpinBox.value())

    def keyReleaseEvent(self, event):
        pass



    def changeOETPattern(self):
        self.dmd.set_image(self.test_image)

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

    def setFunctionGenerator(self):
        v = self.voltageDoubleSpinBox.value()
        f = self.frequencyDoubleSpinBox.value()
        w = self.waveformComboBox.currentText()
        self.function_generator.set_voltage(v)
        self.function_generator.set_frequency(f)
        self.function_generator.set_waveform(w)

    def changeMagnification(self, text):
        idx_dict = {k: v for k, v in zip(self.objectives, range(1, 7))}
        self.microscope.set_objective(idx_dict[text])

    def changeFilter(self, text):
        idx_dict = {k: v for k, v in zip(self.filter_positions, range(1, 7))}
        self.microscope.set_filter(idx_dict[text])

    def toggleFluorShutter(self):
        state = self.fluorescenceShutterPushButton.isChecked()
        if state:
            self.fluorescenceShutterPushButton.setStyleSheet('background-color : lightblue')
        else:
            self.fluorescenceShutterPushButton.setStyleSheet('background-color : lightgrey')
        self.microscope.set_turret_shutter(state)

    def toggleDia(self):
        state = self.diaPushButton.isChecked()
        if state:
            self.diaPushButton.setStyleSheet('background-color : lightblue')
        else:
            self.diaPushButton.setStyleSheet('background-color : lightgrey')
        self.microscope.set_dia_shutter(state)

    def toggleRotation(self):
        state = self.cameraRotationPushButton.isChecked()
        if state:
            self.cameraRotationPushButton.setStyleSheet('background-color : lightblue')
        else:
            self.cameraRotationPushButton.setStyleSheet('background-color : lightgrey')
        self.camera.rotation = state

    def setCameraExposure(self, exposure):
        self.set_camera_expsure_signal.emit(exposure)

    def setCameraGain(self, gain):
        self.set_camera_gain_signal.emit(gain)




sys._excepthook = sys.excepthook


def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = exception_hook

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    # window.setGeometry(500, 300, 800, 600)
    window.show()
    window.activateWindow()
    sys.exit(app.exec_())
