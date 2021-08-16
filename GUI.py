import copy
import qimage2ndarray
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread
from viewport import ViewPort

class GUI(QtWidgets.QWidget):

    def __init__(self):
        super(GUI, self).__init__()

    def setupUI(self, MainWindow):

        self.setWindowTitle('OET System Control')

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