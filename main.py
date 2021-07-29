import sys
import copy
import PyQt5.QtGui
from PyQt5 import QtCore, QtGui, QtWidgets
from function_generator import FunctionGenerator
from pump import Pump
from microscope import Microscope
from fluorescence_controller import FluorescenceController
from viewport import ViewPort
from stage import Stage
from PyQt5.QtCore import QThread
from mightex import Polygon1000
import cv2
import qimage2ndarray
import matplotlib.pyplot as plt
import numpy as np


class ImageViewer(QtWidgets.QWidget):
    resize_event_signal = QtCore.pyqtSignal(QtCore.QSize, 'PyQt_PyObject')
    click_event_signal = QtCore.pyqtSignal(QtGui.QMouseEvent)
    path_signal = QtCore.pyqtSignal('PyQt_PyObject')
    calibration_signal = QtCore.pyqtSignal('PyQt_PyObject')
    enable_dmd_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.image = QtGui.QImage()
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
        self.ignore_release = True
        self.drawing = False
        self.calibrating = False
        self.robot_paths = []
        self.path_payload = {}
        self.calibration_payload = []
        self.begin_path = None

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        # draw in the center here
        x = int(self.width() / 2 - self.image.width() / 2)  # offset to draw in center
        painter.drawImage(x, 0, self.image)
        self.image = QtGui.QImage()

    # @QtCore.pyqtSlot(QtGui.QImage)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def setImage(self, np_img):
        if len(np_img.shape) > 2:
            # Format_RGB16
            qt_img = qimage2ndarray.array2qimage(np_img)
            self.image = qt_img
        else:
            self.image = QtGui.QImage(np_img.data, self.height(), self.width(), np_img.strides[0],
                                      QtGui.QImage.Format_Grayscale8)
        # self.image = image
        self.image_width = self.image.width()
        self.image_height = self.image.height()
        self.update()

    def sizeHint(self):
        return QtCore.QSize(2060 // 3, 2048 // 3)

    def heightForWidth(self, width):
        return width * 2048 // 2060

    def resizeEvent(self, event):
        # force aspect ratio here
        h = self.height()
        w = int(2060 / 2048 * h)
        self.resize_event_signal.emit(QtCore.QSize(h, w), False)
        self.ignore_release = False

    def mouseReleaseEvent(self, event):
        if not self.ignore_release:
            h = self.height()
            w = int(2060 / 2048 * h)
            self.resize_event_signal.emit(QtCore.QSize(h, w), True)
        if self.drawing:
            # subtract offsets for the x (due to black areas on sides of image)
            offset = (self.width() - self.image_width) // 2
            self.path_payload['start_x'] = self.begin_path.x() - offset
            self.path_payload['start_y'] = self.begin_path.y()
            self.path_payload['end_x'] = event.pos().x() - offset
            self.path_payload['end_y'] = event.pos().y()
            self.path_signal.emit(copy.deepcopy(self.path_payload))

    def mousePressEvent(self, event):
        self.ignore_release = True
        self.click_event_signal.emit(event)
        if self.drawing:
            self.begin_path = event.pos()
        if self.calibrating:
            # just scale this one here...probably could be neater
            offset = (self.width() - self.image_width) // 2
            x_scaled = event.pos().x() / self.width()
            y_scaled = event.pos().y() / self.height()
            self.calibration_payload.append((x_scaled, y_scaled))
            print('point marked:', x_scaled, y_scaled)
            if len(self.calibration_payload) > 2:
                QtWidgets.QMessageBox.about(self, 'Calibration', 'Calibration Complete')
                self.calibrating = False
                self.enable_dmd_signal.emit()
                # now emit
                # self.calibration_signal.emit(self.calibration_payload)


class Window(QtWidgets.QWidget):
    start_video_signal = QtCore.pyqtSignal()
    set_camera_expsure_signal = QtCore.pyqtSignal('PyQt_PyObject')
    screenshot_signal = QtCore.pyqtSignal()
    start_record_video_signal = QtCore.pyqtSignal()
    stop_record_video_signal = QtCore.pyqtSignal()
    enable_robot_detection_signal = QtCore.pyqtSignal('PyQt_PyObject')

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
        self.project_circle_mode = False
        self.project_image_mode = False

        self.takeScreenshotPushButton = QtWidgets.QPushButton(text='Screenshot')

        # MICROSCOPE
        self.filter_positions = ['DAPI', 'GFP', 'Red', 'Brightfield', 'Cy5', 'PE-Cy7']
        self.objectives = ['2x', '4x', '10x', '20x', '40x', 'empty']
        self.magnificationLabel = QtWidgets.QLabel(text='Magnification:')
        self.magnificationComboBoxWidget = QtWidgets.QComboBox()
        self.magnificationComboBoxWidget.addItems(self.objectives)
        self.stageStepSizeLabel = QtWidgets.QLabel('XY Step Size:')
        self.xystageStepSizeDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.xystageStepSizeDoubleSpinBox.setSingleStep(0.005)
        self.xystageStepSizeDoubleSpinBox.setMinimum(0.0000)
        self.xystageStepSizeDoubleSpinBox.setDecimals(3)
        self.xystageStepSizeDoubleSpinBox.setMaximum(5)
        self.xystageStepSizeDoubleSpinBox.setValue(0.005)
        self.xystageStepSizeDoubleSpinBox.setSuffix('mm')
        self.stageXYSpeedLabel = QtWidgets.QLabel('XY Step Speed:')
        self.stageXYSpeedDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.stageXYSpeedDoubleSpinBox.setSingleStep(0.005)
        self.stageXYSpeedDoubleSpinBox.setSuffix('mm/s')
        self.stageXYStartAccelerationLabel = QtWidgets.QLabel('XY Start Acceleration:')
        self.stageXYStartAccelerationDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.stageXYStartAccelerationDoubleSpinBox.setSingleStep(0.05)
        self.stageXYStartAccelerationDoubleSpinBox.setSuffix('mm/s\u00B2')
        self.stageXYStopAccelerationLabel = QtWidgets.QLabel('XY Stop Acceleration:')
        self.stageXYStopAccelerationDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.stageXYStopAccelerationDoubleSpinBox.setSingleStep(0.05)
        self.stageXYStopAccelerationDoubleSpinBox.setSuffix('mm/s\u00B2')
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
        self.diaShutterPushButton = QtWidgets.QPushButton('Dia Shutter')
        self.diaShutterPushButton.setCheckable(True)
        self.diaLightPushbutton = QtWidgets.QPushButton('Dia Lamp')
        self.diaLightPushbutton.setCheckable(True)
        self.diaVoltageLabel = QtWidgets.QLabel('Voltage:')
        self.diaVoltageDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.diaVoltageDoubleSpinBox.setMinimum(5)
        self.diaVoltageDoubleSpinBox.setMaximum(100)
        self.diaVoltageDoubleSpinBox.setSingleStep(5)
        self.diaVoltageDoubleSpinBox.setSuffix('%')
        self.cameraExposureLabel = QtWidgets.QLabel('Exposure:')
        self.cameraExposureDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.cameraExposureDoubleSpinBox.setSuffix('ms')
        self.cameraExposureDoubleSpinBox.setMaximum(5000)
        self.cameraExposureDoubleSpinBox.setMinimum(5)
        self.cameraExposureDoubleSpinBox.setSingleStep(20)
        self.cameraExposureDoubleSpinBox.setValue(200)

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
        self.fluorescenceIntensityDoubleSpinBox.setMinimum(5)
        self.fluorescenceIntensityDoubleSpinBox.setMaximum(100)
        self.fluorescenceIntensityDoubleSpinBox.setSingleStep(5)
        self.fluorescenceShutterPushButton = QtWidgets.QPushButton('Shutter')
        self.fluorescenceShutterPushButton.setCheckable(True)
        self.fluorescenceToggleLampPushButton = QtWidgets.QPushButton('Lamp')
        self.fluorescenceToggleLampPushButton.setCheckable(True)

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
        self.oetClearOverlayPushButton = QtWidgets.QPushButton('Clear Paths')
        self.oetCalibratePushButton = QtWidgets.QPushButton('Calibrate')
        self.oetRunPushButton = QtWidgets.QPushButton('Run')
        self.oetScaleLabel = QtWidgets.QLabel('Scale:')
        self.oetScaleDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.oetScaleDoubleSpinBox.setSuffix('%')
        self.oetScaleDoubleSpinBox.setSingleStep(5)
        self.oetScaleDoubleSpinBox.setMinimum(5)
        self.oetScaleDoubleSpinBox.setDecimals(0)
        self.oetRotationLabel = QtWidgets.QLabel('Rotation:')
        self.oetRotationDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.oetRotationDoubleSpinBox.setSuffix('°')
        self.oetRotationDoubleSpinBox.setDecimals(0)
        self.oetRotationDoubleSpinBox.setMinimum(5)
        self.oetRotationDoubleSpinBox.setMaximum(180)
        self.oetRotationDoubleSpinBox.setSingleStep(5)
        self.oetTranslateLabel = QtWidgets.QLabel('Translation:')
        self.oetTranslateDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.oetTranslateDoubleSpinBox.setValue(5)
        self.oetScaleUpPushButton = QtWidgets.QPushButton('Scale Up')
        self.oetScaleDownPushButton = QtWidgets.QPushButton('Scale Down')
        self.oetProjectCirclePushButton = QtWidgets.QPushButton('Project Circle')
        self.oetProjectCirclePushButton.setCheckable(True)
        self.oetLoadProjectionImagePushButton = QtWidgets.QPushButton('Load Projection Image')
        self.oetProjectImagePushButton = QtWidgets.QPushButton('Project Image')
        self.oetProjectImagePushButton.setCheckable(True)
        self.oetClearPushButton = QtWidgets.QPushButton('Clear Projection')
        self.oetToggleLampPushButton = QtWidgets.QPushButton('Lamp')
        self.oetToggleLampPushButton.setCheckable(True)
        self.oetLampIntesnsityLabel = QtWidgets.QLabel('Intensity:')
        self.oetLampIntesnsityDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.oetLampIntesnsityDoubleSpinBox.setSuffix('%')
        self.oetLampIntesnsityDoubleSpinBox.setMaximum(100)
        self.oetLampIntesnsityDoubleSpinBox.setDecimals(1)
        self.oetLampIntesnsityDoubleSpinBox.setSingleStep(5)

        # arrange the widgets
        self.VBoxLayout = QtWidgets.QVBoxLayout()
        self.HBoxLayout = QtWidgets.QHBoxLayout(self)

        self.microscopeGroupBox = QtWidgets.QGroupBox('Microscope')
        self.microscopeLayout = QtWidgets.QVBoxLayout()
        self.microscopeGroupBox.setLayout(self.microscopeLayout)

        self.microscopeLayoutUpper = QtWidgets.QHBoxLayout()
        self.microscopeLayoutUpper.addWidget(self.stageStepSizeLabel)
        self.microscopeLayoutUpper.addWidget(self.xystageStepSizeDoubleSpinBox)
        self.microscopeLayoutUpper.addWidget(self.stageXYSpeedLabel)
        self.microscopeLayoutUpper.addWidget(self.stageXYSpeedDoubleSpinBox)
        self.microscopeLayoutUpper.addWidget(self.stageXYStartAccelerationLabel)
        self.microscopeLayoutUpper.addWidget(self.stageXYStartAccelerationDoubleSpinBox)
        self.microscopeLayoutUpper.addWidget(self.stageXYStopAccelerationLabel)
        self.microscopeLayoutUpper.addWidget(self.stageXYStopAccelerationDoubleSpinBox)
        self.microscopeLayoutUpper.addWidget(self.zstageStepSizeLabel)
        self.microscopeLayoutUpper.addWidget(self.zstageStepSizeDoubleSpinBox)
        self.microscopeLayoutUpper.setAlignment(QtCore.Qt.AlignLeft)
        self.microscopeLayout.addLayout(self.microscopeLayoutUpper)

        self.microscopeLayoutLower = QtWidgets.QHBoxLayout()
        self.microscopeLayoutLower.addWidget(self.magnificationLabel)
        self.microscopeLayoutLower.addWidget(self.magnificationComboBoxWidget)
        self.microscopeLayoutLower.addWidget(self.filterLabel)
        self.microscopeLayoutLower.addWidget(self.filterComboBoxWidget)
        self.microscopeLayoutLower.addWidget(self.diaShutterPushButton)
        self.microscopeLayoutLower.addWidget(self.diaLightPushbutton)
        self.microscopeLayoutLower.addWidget(self.diaVoltageLabel)
        self.microscopeLayoutLower.addWidget(self.diaVoltageDoubleSpinBox)
        self.microscopeLayoutLower.addWidget(self.cameraExposureLabel)
        self.microscopeLayoutLower.addWidget(self.cameraExposureDoubleSpinBox)
        self.microscopeLayoutLower.addWidget(self.cameraRotationPushButton)
        self.microscopeLayout.addLayout(self.microscopeLayoutLower)

        self.microscopeLayoutLower.setAlignment(QtCore.Qt.AlignLeft)
        self.VBoxLayout.addWidget(self.microscopeGroupBox)
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
        self.functionGeneratorLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.VBoxLayout.addWidget(self.functionGeneratorGroupBox)
        if not self.function_generator:
            self.functionGeneratorGroupBox.setEnabled(False)

        self.fluorescenceGroupBox = QtWidgets.QGroupBox('Fluorescence')
        self.fluorescenceLayout = QtWidgets.QHBoxLayout()
        self.fluorescenceGroupBox.setLayout(self.fluorescenceLayout)
        self.fluorescenceLayout.addWidget(self.fluorescenceShutterPushButton)
        self.fluorescenceLayout.addWidget(self.fluorescenceToggleLampPushButton)
        self.fluorescenceLayout.addWidget(self.fluorescenceIntensityLabel)
        self.fluorescenceLayout.addWidget(self.fluorescenceIntensityDoubleSpinBox)
        self.fluorescenceLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.VBoxLayout.addWidget(self.fluorescenceGroupBox)
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
        self.VBoxLayout.addWidget(self.pumpGroupBox)
        if not self.pump:
            self.pumpGroupBox.setEnabled(False)

        self.oetGroupBox = QtWidgets.QGroupBox('OET Controls')
        self.oetLayout = QtWidgets.QVBoxLayout()
        self.oetGroupBox.setLayout(self.oetLayout)

        self.oetLayoutUpper = QtWidgets.QHBoxLayout()
        self.oetLayoutUpper.addWidget(self.detectRobotsPushButton)
        self.detectRobotsPushButton.setCheckable(True)
        self.oetLayoutUpper.addWidget(self.drawPathsPushButton)
        self.oetLayoutUpper.addWidget(self.oetClearOverlayPushButton)
        self.oetLayoutUpper.addWidget(self.oetRunPushButton)
        self.oetLayoutUpper.addWidget(self.oetCalibratePushButton)
        self.oetLayoutUpper.addWidget(self.oetClearPushButton)
        self.oetLayoutUpper.addWidget(self.oetToggleLampPushButton)
        self.oetLayoutUpper.addWidget(self.oetLampIntesnsityLabel)
        self.oetLayoutUpper.addWidget(self.oetLampIntesnsityDoubleSpinBox)
        self.oetLayoutUpper.setAlignment(QtCore.Qt.AlignLeft)
        self.oetLayout.addLayout(self.oetLayoutUpper)

        self.oetLayoutLower = QtWidgets.QHBoxLayout()
        self.oetLayoutLower.addWidget(self.oetProjectCirclePushButton)
        self.oetLayoutLower.addWidget(self.oetLoadProjectionImagePushButton)
        self.oetLayoutLower.addWidget(self.oetProjectImagePushButton)
        self.oetLayoutLower.addWidget(self.oetScaleLabel)
        self.oetLayoutLower.addWidget(self.oetScaleDoubleSpinBox)
        self.oetLayoutLower.addWidget(self.oetScaleUpPushButton)
        self.oetLayoutLower.addWidget(self.oetScaleDownPushButton)
        self.oetLayoutLower.addWidget(self.oetRotationLabel)
        self.oetLayoutLower.addWidget(self.oetRotationDoubleSpinBox)
        self.oetLayoutLower.addWidget(self.oetTranslateLabel)
        self.oetLayoutLower.addWidget(self.oetTranslateDoubleSpinBox)
        self.oetLayoutLower.setAlignment(QtCore.Qt.AlignLeft)
        self.oetLayout.addLayout(self.oetLayoutLower)
        # if not self.dmd:
        #     self.oetGroupBox.setEnabled(False)

        self.takeVideoPushbutton = QtWidgets.QPushButton('Record Video')
        self.takeVideoPushbutton.setCheckable(True)

        self.VBoxLayout.addWidget(self.oetGroupBox)
        self.VBoxLayout.addWidget(self.takeScreenshotPushButton)
        self.VBoxLayout.addWidget(self.takeVideoPushbutton)

        self.image_viewer = ImageViewer()

        # TODO: fix this...
        # self.image_viewer.calibration_signal.connect(self.dmd.calibration_slot)

        self.camera = ViewPort()
        self.camera_thread = QThread()
        self.camera_thread.start()

        self.image_viewer.resize_event_signal.connect(self.camera.resize_slot)
        self.image_viewer.path_signal.connect(self.camera.path_slot)

        self.set_camera_expsure_signal.connect(self.camera.set_exposure_slot)

        self.camera.VideoSignal.connect(self.image_viewer.setImage)
        self.image_viewer.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.camera.moveToThread(self.camera_thread)

        self.image_viewer.click_event_signal.connect(self.handle_click)

        self.VBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        self.HBoxLayout.addLayout(self.VBoxLayout)
        self.HBoxLayout.addWidget(self.image_viewer)
        self.initialize_gui_state()
        self.showMaximized()

        # connect to the video thread and start the video
        self.start_video_signal.connect(self.camera.startVideo)
        self.setChildrenFocusPolicy(QtCore.Qt.ClickFocus)
        self.start_video_signal.emit()

    def initialize_gui_state(self):
        # get the initial state and make the GUI synced to it
        idx_dict = {k: v for k, v in zip(range(1, 7), self.objectives)}
        objective = self.microscope.status.iNOSEPIECE
        self.magnificationComboBoxWidget.setCurrentText(idx_dict[objective])

        idx_dict = {k: v for k, v in zip(range(1, 7), self.filter_positions)}
        filter = self.microscope.status.iTURRET1POS
        self.filterComboBoxWidget.setCurrentText(idx_dict[filter])

        fluor_shutter_state = self.microscope.status.iTURRET1SHUTTER
        self.fluorescenceShutterPushButton.setChecked(fluor_shutter_state)

        dia_state = self.microscope.status.iSHUTTER_DIA
        self.diaShutterPushButton.setChecked(dia_state)


        xy_vel = self.stage.get_xy_vel()
        self.stageXYSpeedDoubleSpinBox.setValue(xy_vel)
        self.stageXYSpeedDoubleSpinBox.valueChanged.connect(self.stage.set_xy_vel)
        xy_start_accel, xy_stop_accel = self.stage.get_xy_accels()
        self.stageXYStartAccelerationDoubleSpinBox.setValue(xy_start_accel)
        self.stageXYStopAccelerationDoubleSpinBox.setValue(xy_stop_accel)
        self.stageXYStopAccelerationDoubleSpinBox.valueChanged.connect(self.stage.set_xy_stop_accel)
        self.stageXYStartAccelerationDoubleSpinBox.valueChanged.connect(self.stage.set_xy_start_accel)


        # connect all of our control signals
        self.takeScreenshotPushButton.clicked.connect(self.camera.take_screenshot_slot)
        self.start_record_video_signal.connect(self.camera.start_recording_video_slot)
        self.stop_record_video_signal.connect(self.camera.stop_video_slot)
        self.takeVideoPushbutton.clicked.connect(self.toggleVideoRecording)

        self.magnificationComboBoxWidget.currentTextChanged.connect(self.changeMagnification)
        self.xystageStepSizeDoubleSpinBox.valueChanged.connect(self.stage.set_xystep_size)
        self.zstageStepSizeDoubleSpinBox.valueChanged.connect(self.microscope.set_zstep_size)
        self.filterComboBoxWidget.currentTextChanged.connect(self.changeFilter)
        self.diaShutterPushButton.clicked.connect(self.toggleDiaShutter)
        self.diaLightPushbutton.clicked.connect(self.toggleDiaLamp)
        self.diaVoltageDoubleSpinBox.valueChanged.connect(self.microscope.set_dia_voltage)
        self.cameraExposureDoubleSpinBox.valueChanged.connect(self.setCameraExposure)
        self.cameraRotationPushButton.clicked.connect(self.toggleRotation)
        if self.function_generator:
            self.fgOutputCombobox.currentTextChanged.connect(self.function_generator.change_output)
        self.setFunctionGeneratorPushButton.clicked.connect(self.setFunctionGenerator)
        self.fluorescenceIntensityDoubleSpinBox.valueChanged.connect(self.fluorescence_controller.change_intensity)
        self.fluorescenceToggleLampPushButton.clicked.connect(self.toggleFLuorescenceLamp)
        self.fluorescenceShutterPushButton.clicked.connect(self.toggleFluorShutter)
        self.pumpAmountRadioButton.clicked.connect(self.startAmountDispenseMode)
        self.pumpTimeRadioButton.clicked.connect(self.startTimeDispenseMode)
        self.pumpDispensePushButton.clicked.connect(self.pumpDispense)
        self.pumpWithdrawPushButton.clicked.connect(self.pumpWithdraw)
        self.pumpStopPushButton.clicked.connect(self.pump.halt)
        self.pumpTimeRadioButton.click()

        self.drawPathsPushButton.clicked.connect(self.toggleDrawPaths)
        self.detectRobotsPushButton.clicked.connect(self.turn_on_robot_detection)
        self.enable_robot_detection_signal.connect(self.camera.enable_detection_slot)
        self.oetClearOverlayPushButton.clicked.connect(self.camera.clear_paths_overlay_slot)

        self.oetCalibratePushButton.clicked.connect(self.calibrate_dmd)
        self.oetClearPushButton.clicked.connect(self.dmd.clear_oet_projection)
        self.oetProjectCirclePushButton.clicked.connect(self.toggle_project_circle)
        self.oetLoadProjectionImagePushButton.clicked.connect(self.load_oet_projection)
        self.oetProjectImagePushButton.clicked.connect(self.toggle_project_image)
        self.oetScaleUpPushButton.clicked.connect(self.scale_up_oet_projection)
        self.oetScaleDownPushButton.clicked.connect(self.scale_down_oet_projection)
        self.oetToggleLampPushButton.clicked.connect(self.toggle_dmd_lamp)
        self.oetLampIntesnsityDoubleSpinBox.valueChanged.connect(self.dmd.set_dmd_current)

        self.image_viewer.enable_dmd_signal.connect(self.enable_dmd_controls)

        self.oetScaleDownPushButton.setEnabled(False)
        self.oetProjectCirclePushButton.setEnabled(False)
        self.oetLoadProjectionImagePushButton.setEnabled(False)
        self.oetProjectImagePushButton.setEnabled(False)
        self.oetScaleDoubleSpinBox.setEnabled(False)
        self.oetRotationDoubleSpinBox.setEnabled(False)
        self.oetTranslateDoubleSpinBox.setEnabled(False)
        self.oetScaleUpPushButton.setEnabled(False)

        self.dmd.initialize_dmd()
        self.fluorescence_controller.turn_all_off()

    def turn_on_robot_detection(self):
        state = self.detectRobotsPushButton.isChecked()
        if state:
            self.detectRobotsPushButton.setStyleSheet('background-color : lightblue')
        else:
            self.detectRobotsPushButton.setStyleSheet('background-color : lightgrey')
        self.enable_robot_detection_signal.emit(state)


    def toggleVideoRecording(self):
        state = self.takeVideoPushbutton.isChecked()
        if state:
            self.takeVideoPushbutton.setStyleSheet('background-color : lightblue')
        else:
            self.takeVideoPushbutton.setStyleSheet('background-color : lightgrey')
        if state:
            self.start_record_video_signal.emit()
        else:
            self.stop_record_video_signal.emit()

    def toggleFLuorescenceLamp(self):
        state = self.fluorescenceToggleLampPushButton.isChecked()
        if state:
            self.fluorescenceToggleLampPushButton.setStyleSheet('background-color : lightblue')
        else:
            self.fluorescenceToggleLampPushButton.setStyleSheet('background-color : lightgrey')
        if state:
            self.fluorescence_controller.turn_led_on()
        else:
            self.fluorescence_controller.turn_all_off()

    def toggle_dmd_lamp(self):
        state = self.oetToggleLampPushButton.isChecked()
        if state:
            self.oetToggleLampPushButton.setStyleSheet('background-color : lightblue')
        else:
            self.oetToggleLampPushButton.setStyleSheet('background-color : lightgrey')
        self.dmd.toggle_dmd_light(state)

    def scale_up_oet_projection(self):
        amt = self.oetScaleDoubleSpinBox.value()
        self.dmd.scale_projection(1 + amt / 100)

    def scale_down_oet_projection(self):
        amt = self.oetScaleDoubleSpinBox.value()
        self.dmd.scale_projection(1 - amt / 100)

    def load_oet_projection(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file for projection')
        if file_name != '':
            self.dmd.load_projection_image(file_name)
            self.oetProjectImagePushButton.setEnabled(True)


    def calibrate_dmd(self):
        print('calibrating dmd...')
        # no we want to project 3 circles on the dmd for the user to click so that we can calibrate
        QtWidgets.QMessageBox.about(self, 'Calibration',
                                    'Please click the center of the 3 (clipped) projected circles in a CLOCKWISE \
                                    fashion to calibrate the DMD.')
        self.dmd.project_calibration_image()
        self.image_viewer.calibration_payload = []
        self.image_viewer.calibrating = True

    @QtCore.pyqtSlot()
    def enable_dmd_controls(self):
        self.oetScaleDownPushButton.setEnabled(True)
        self.oetProjectCirclePushButton.setEnabled(True)
        self.oetLoadProjectionImagePushButton.setEnabled(True)
        self.oetProjectImagePushButton.setEnabled(True)
        self.oetScaleDoubleSpinBox.setEnabled(True)
        self.oetRotationDoubleSpinBox.setEnabled(True)
        self.oetTranslateDoubleSpinBox.setEnabled(True)
        self.oetScaleUpPushButton.setEnabled(True)

    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def handle_click(self, event):
        # see if we are calibrated
        if len(self.image_viewer.calibration_payload) < 3:
            return
        x = event.pos().x()
        y = event.pos().y()

        # scale everything
        scaled_x = x / self.image_viewer.width()
        scaled_y = y / self.image_viewer.height()

        # check if we can illuminate the clicked area with the dmd
        check = self.check_if_in_dmd_area(scaled_x, scaled_y)
        if not check:
            print('not within DMD area. ignoring click')
            return

        # get the full scale of our dmd area
        FS_x = self.image_viewer.calibration_payload[-1][0] - self.image_viewer.calibration_payload[0][0]
        FS_y = self.image_viewer.calibration_payload[-1][1] - self.image_viewer.calibration_payload[0][1]

        # subtract out our top left calibration spot and divide by full scale
        dmd_scaled_x = (scaled_x - self.image_viewer.calibration_payload[0][0]) / FS_x
        dmd_scaled_y = (scaled_y - self.image_viewer.calibration_payload[0][1]) / FS_y

        # project in the proper mode
        if self.project_circle_mode:
            self.dmd.project_circle(dmd_scaled_x, dmd_scaled_y)
        elif self.project_image_mode:
            self.dmd.project_loaded_image(dmd_scaled_x, dmd_scaled_y)

    def toggle_project_circle(self):
        self.project_circle_mode = self.oetProjectCirclePushButton.isChecked()
        self.oetProjectImagePushButton.setChecked(False)
        self.project_image_mode = False

    def toggle_project_image(self):
        self.project_image_mode = self.oetProjectImagePushButton.isChecked()
        self.oetProjectCirclePushButton.setChecked(False)
        self.project_circle_mode = False

    def toggleDrawPaths(self):
        state = self.drawPathsPushButton.isChecked()
        self.image_viewer.drawing = state

    def closeEvent(self, event):
        print('closing all connections...')
        for hardware in [self.microscope, self.fluorescence_controller, self.function_generator,
                         self.dmd, self.pump]:
            if hardware is not False:
                hardware.__del__()

    def setChildrenFocusPolicy(self, policy):
        def recursiveSetChildFocusPolicy(parentQWidget):
            for childQWidget in parentQWidget.findChildren(QtWidgets.QWidget):
                if isinstance(childQWidget, QtWidgets.QComboBox) or isinstance(childQWidget, QtWidgets.QComboBox):
                    # make all comboboxes respond to nothing at all
                    childQWidget.setFocusPolicy(QtCore.Qt.NoFocus)
                else:
                    childQWidget.setFocusPolicy(policy)
                recursiveSetChildFocusPolicy(childQWidget)

        recursiveSetChildFocusPolicy(self)

    def keyPressEvent(self, event):
        key = event.key()
        if self.project_image_mode:
            rotate_amt = self.oetRotationDoubleSpinBox.value()
            translate_amt = self.oetTranslateDoubleSpinBox.value()
            if key == QtCore.Qt.Key_Q:
                self.dmd.rotate_projection_image(rotate_amt)
            elif key == QtCore.Qt.Key_E:
                self.dmd.rotate_projection_image(-rotate_amt)
            elif key == QtCore.Qt.Key_W:
                self.dmd.translate(-translate_amt)
            elif key == QtCore.Qt.Key_S:
                self.dmd.translate(+translate_amt)
            elif key == QtCore.Qt.Key_A:
                self.dmd.strafe(translate_amt)
            elif key == QtCore.Qt.Key_D:
                self.dmd.strafe(-translate_amt)
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
                self.stage.step('r')
            elif key == QtCore.Qt.Key_Left:
                self.stage.step('u')
            elif key == QtCore.Qt.Key_Right:
                self.stage.step('d')
            elif key == QtCore.Qt.Key_Down:
                self.stage.step('l')
        if key == QtCore.Qt.Key_PageUp:
            self.microscope.move_rel_z(self.zstageStepSizeDoubleSpinBox.value())
        elif key == QtCore.Qt.Key_PageDown:
            self.microscope.move_rel_z(-self.zstageStepSizeDoubleSpinBox.value())

    def keyReleaseEvent(self, event):
        pass

    def check_if_in_dmd_area(self, scaled_x, scaled_y):
        # define bounds
        min_x = self.image_viewer.calibration_payload[0][0]
        max_x = self.image_viewer.calibration_payload[-1][0]

        min_y = self.image_viewer.calibration_payload[0][1]
        max_y = self.image_viewer.calibration_payload[-1][1]

        if min_x < scaled_x < max_x and min_y < scaled_y < max_y:
            return True
        else:
            return False



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

    def toggleDiaShutter(self):
        state = self.diaShutterPushButton.isChecked()
        if state:
            self.diaShutterPushButton.setStyleSheet('background-color : lightblue')
        else:
            self.diaShutterPushButton.setStyleSheet('background-color : lightgrey')
        self.microscope.set_dia_shutter(state)

    def toggleDiaLamp(self):
        state = self.diaLightPushbutton.isChecked()
        if state:
            self.diaLightPushbutton.setStyleSheet('background-color : lightblue')
        else:
            self.diaLightPushbutton.setStyleSheet('background-color : lightgrey')
        self.microscope.toggle_dia_light(state)

    def toggleRotation(self):
        state = self.cameraRotationPushButton.isChecked()
        if state:
            self.cameraRotationPushButton.setStyleSheet('background-color : lightblue')
        else:
            self.cameraRotationPushButton.setStyleSheet('background-color : lightgrey')
        self.camera.rotation = state

    def setCameraExposure(self, exposure):
        self.set_camera_expsure_signal.emit(exposure)


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
