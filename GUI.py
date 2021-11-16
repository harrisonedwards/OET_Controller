import copy
import qimage2ndarray
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, Qt
from image_processor import imageProcessor
import logging
import cv2

class GUI(QtWidgets.QMainWindow):

    def __init__(self):
        super(GUI, self).__init__()

    def setupUI(self, MainWindow):

        self.setWindowTitle('OET System Control')
        self.statusBar = self.statusBar()

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
        self.stageXYSpeedDoubleSpinBox.setDecimals(3)
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
        self.zstageStepSizeDoubleSpinBox.setMinimum(50)
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
        self.scaleBarTogglePushButton = QtWidgets.QPushButton('Scale Bar')
        self.scaleBarTogglePushButton.setCheckable(True)

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
        self.fgOutputTogglePushButton = QtWidgets.QPushButton('Output')
        self.fgOutputTogglePushButton.setCheckable(True)
        self.pulseLabel = QtWidgets.QLabel('Pulse Duration:')
        self.pulseDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.pulseDoubleSpinBox.setSuffix('ms')
        self.pulseDoubleSpinBox.setMinimum(0)
        self.pulseDoubleSpinBox.setDecimals(3)
        self.pulseDoubleSpinBox.setMaximum(5000)
        self.pulsePushButton = QtWidgets.QPushButton('Pulse')

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
        self.detectRobotsPushButton.setCheckable(True)
        self.bufferSizeLabel = QtWidgets.QLabel('Buffer:')
        self.bufferSizeDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.bufferSizeDoubleSpinBox.setSuffix('px')
        self.bufferSizeDoubleSpinBox.setDecimals(0)
        self.bufferSizeDoubleSpinBox.setSingleStep(5)
        self.bufferSizeDoubleSpinBox.setValue(10)
        self.dilationSizeLabel = QtWidgets.QLabel('Dilation:')
        self.dilationSizeDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.dilationSizeDoubleSpinBox.setSuffix('px')
        self.dilationSizeDoubleSpinBox.setDecimals(0)
        self.dilationSizeDoubleSpinBox.setSingleStep(5)
        self.dilationSizeDoubleSpinBox.setValue(30)

        self.drawPathsPushButton = QtWidgets.QPushButton('Draw Paths')
        self.drawPathsPushButton.setCheckable(True)
        self.drawShapePushButton = QtWidgets.QPushButton('Draw Shape')
        self.drawShapePushButton.setCheckable(True)
        self.oetClearOverlayPushButton = QtWidgets.QPushButton('Clear Paths')
        self.oetCalibratePushButton = QtWidgets.QPushButton('Calibrate')
        self.oetProjectDetectionPushButton = QtWidgets.QPushButton('Project Detection Pattern')
        self.oetOpenRobotsPushButton = QtWidgets.QPushButton('Open Robots')
        self.oetOpenRobotsPushButton.setCheckable(True)
        self.oetControlDetectedPushButton = QtWidgets.QPushButton('Control Detected Robot')
        self.oetControlDetectedPushButton.setCheckable(True)
        self.oetScaleLabel = QtWidgets.QLabel('Scale:')
        self.oetScaleDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.oetScaleDoubleSpinBox.setSuffix('%')
        self.oetScaleDoubleSpinBox.setSingleStep(10)
        self.oetScaleDoubleSpinBox.setMinimum(-50)
        self.oetScaleDoubleSpinBox.setMaximum(50)
        self.oetScaleDoubleSpinBox.setDecimals(0)
        self.oetScaleDoubleSpinBox.setValue(-5)
        self.oetRotationLabel = QtWidgets.QLabel('Rotation:')
        self.oetRotationDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.oetRotationDoubleSpinBox.setSuffix('°')
        self.oetRotationDoubleSpinBox.setDecimals(0)
        self.oetRotationDoubleSpinBox.setMinimum(1)
        self.oetRotationDoubleSpinBox.setMaximum(180)
        self.oetRotationDoubleSpinBox.setSingleStep(5)
        self.oetTranslateLabel = QtWidgets.QLabel('Translation:')
        self.oetTranslateDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.oetTranslateDoubleSpinBox.setValue(5)
        self.oetScaleUpPushButton = QtWidgets.QPushButton('Scale Image')
        self.oetProjectCirclePushButton = QtWidgets.QPushButton('Project Circle')
        self.oetProjectCirclePushButton.setCheckable(True)
        self.oetLoadProjectionImagePushButton = QtWidgets.QPushButton('Load Projection Image')
        self.oetProjectImagePushButton = QtWidgets.QPushButton('Project Image')
        self.oetProjectImagePushButton.setCheckable(True)
        self.oetControlProjectionsPushButton = QtWidgets.QPushButton('Control Projections')
        self.oetControlProjectionsPushButton.setCheckable(True)
        self.oetClearPushButton = QtWidgets.QPushButton('Clear Controls')
        self.oetToggleLampPushButton = QtWidgets.QPushButton('Lamp')
        self.oetToggleLampPushButton.setCheckable(True)
        self.oetLampIntesnsityLabel = QtWidgets.QLabel('Intensity:')
        self.oetLampIntesnsityDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.oetLampIntesnsityDoubleSpinBox.setSuffix('%')
        self.oetLampIntesnsityDoubleSpinBox.setMaximum(100)
        self.oetLampIntesnsityDoubleSpinBox.setDecimals(1)
        self.oetLampIntesnsityDoubleSpinBox.setSingleStep(5)

        self.imageAdjustmentClahePushButton = QtWidgets.QPushButton('Apply Clahe')
        self.imageAdjustmentClahePushButton.setCheckable(True)
        self.imageAdjustmentClaheGridLabel = QtWidgets.QLabel('Grid Size:')
        self.imageAdjustmentClaheGridValueDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.imageAdjustmentClaheGridValueDoubleSpinBox.setMinimum(3)
        self.imageAdjustmentClaheGridValueDoubleSpinBox.setMaximum(200)
        self.imageAdjustmentClaheGridValueDoubleSpinBox.setSingleStep(2)
        self.imageAdjustmentClaheGridValueDoubleSpinBox.setDecimals(0)
        self.imageAdjustmentClaheClipValueLabel = QtWidgets.QLabel('Clip Limit:')
        self.imageAdjustmentClaheClipValueDoubleSpinBox = QtWidgets.QDoubleSpinBox()
        self.imageAdjustmentClaheClipValueDoubleSpinBox.setMinimum(1)
        self.imageAdjustmentClaheClipValueDoubleSpinBox.setMaximum(200)
        self.imageAdjustmentClaheClipValueDoubleSpinBox.setSingleStep(1)
        self.imageAdjustmentClaheClipValueDoubleSpinBox.setDecimals(1)
        self.imageAdjustmentThresholdPushButton = QtWidgets.QPushButton('Threshold')
        self.imageAdjustmentThresholdPushButton.setCheckable(True)
        self.imageAdjustmentThresholdSlider = QtWidgets.QSlider(Qt.Horizontal)
        self.imageAdjustmentThresholdSlider.setMaximum(100)
        self.imageAdjustmentThresholdLabel = QtWidgets.QLabel('0')

        self.takeScreenshotPushButton = QtWidgets.QPushButton(text='Screenshot')
        self.takeVideoPushbutton = QtWidgets.QPushButton('Record Video')
        self.takeVideoPushbutton.setCheckable(True)

        #
        # ARRANGE THE WIDGETS
        #

        centralWidget = QtWidgets.QWidget(self)
        self.VBoxLayout = QtWidgets.QVBoxLayout()
        self.HBoxLayout = QtWidgets.QHBoxLayout(centralWidget)
        centralWidget.setLayout(self.HBoxLayout)
        self.setCentralWidget(centralWidget)

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
        self.microscopeLayoutLower.addWidget(self.scaleBarTogglePushButton)
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
        self.functionGeneratorLayout.addWidget(self.fgOutputTogglePushButton)
        self.functionGeneratorLayout.addWidget(self.pulseLabel)
        self.functionGeneratorLayout.addWidget(self.pulseDoubleSpinBox)
        self.functionGeneratorLayout.addWidget(self.pulsePushButton)

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
        if not self.pump.ser:
            self.pumpGroupBox.setEnabled(False)

        self.oetGroupBox = QtWidgets.QGroupBox('OET Controls')
        self.oetLayout = QtWidgets.QVBoxLayout()
        self.oetGroupBox.setLayout(self.oetLayout)
        self.oetLayoutUpper = QtWidgets.QHBoxLayout()
        self.oetLayoutUpper.addWidget(self.detectRobotsPushButton)
        self.oetLayoutUpper.addWidget(self.bufferSizeLabel)
        self.oetLayoutUpper.addWidget(self.bufferSizeDoubleSpinBox)
        self.oetLayoutUpper.addWidget(self.dilationSizeLabel)
        self.oetLayoutUpper.addWidget(self.dilationSizeDoubleSpinBox)
        self.oetLayoutUpper.addWidget(self.drawPathsPushButton)
        self.oetLayoutUpper.addWidget(self.drawShapePushButton)
        self.oetLayoutUpper.addWidget(self.oetClearOverlayPushButton)
        self.oetLayoutUpper.addWidget(self.oetCalibratePushButton)
        self.oetLayoutUpper.addWidget(self.oetClearPushButton)
        self.oetLayoutUpper.addWidget(self.oetToggleLampPushButton)
        self.oetLayoutUpper.addWidget(self.oetLampIntesnsityLabel)
        self.oetLayoutUpper.addWidget(self.oetLampIntesnsityDoubleSpinBox)
        self.oetLayoutUpper.setAlignment(QtCore.Qt.AlignLeft)
        self.oetLayout.addLayout(self.oetLayoutUpper)

        self.oetLayoutMiddle = QtWidgets.QHBoxLayout()
        self.oetLayoutMiddle.addWidget(self.oetProjectCirclePushButton)
        self.oetLayoutMiddle.addWidget(self.oetLoadProjectionImagePushButton)
        self.oetLayoutMiddle.addWidget(self.oetProjectImagePushButton)
        self.oetLayoutMiddle.addWidget(self.oetControlProjectionsPushButton)
        self.oetLayoutMiddle.addWidget(self.oetProjectDetectionPushButton)
        self.oetLayoutMiddle.addWidget(self.oetOpenRobotsPushButton)
        self.oetLayoutMiddle.addWidget(self.oetControlDetectedPushButton)
        self.oetLayout.addLayout(self.oetLayoutMiddle)

        self.oetLayoutLower = QtWidgets.QHBoxLayout()
        self.oetLayoutLower.addWidget(self.oetScaleLabel)
        self.oetLayoutLower.addWidget(self.oetScaleDoubleSpinBox)
        self.oetLayoutLower.addWidget(self.oetScaleUpPushButton)
        self.oetLayoutLower.addWidget(self.oetRotationLabel)
        self.oetLayoutLower.addWidget(self.oetRotationDoubleSpinBox)
        self.oetLayoutLower.addWidget(self.oetTranslateLabel)
        self.oetLayoutLower.addWidget(self.oetTranslateDoubleSpinBox)
        self.oetLayoutLower.setAlignment(QtCore.Qt.AlignLeft)

        self.oetRobotsGroupBox = QtWidgets.QGroupBox('Robots')
        self.oetRobotsLayout = QtWidgets.QHBoxLayout()
        self.oetRobotsGroupBox.setLayout(self.oetRobotsLayout)
        self.oetRobotsLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.oetRobotsEmptyLabel = QtWidgets.QLabel('(empty)')
        self.oetRobotsLayout.addWidget(self.oetRobotsEmptyLabel)
        self.oetLayoutBottom = QtWidgets.QHBoxLayout()
        self.oetLayout.addWidget(self.oetRobotsGroupBox)
        self.oetRobotsGroupBox.setEnabled(False)

        self.oetLayout.addLayout(self.oetLayoutLower)
        self.VBoxLayout.addWidget(self.oetGroupBox)
        if not self.dmd:
            self.oetGroupBox.setEnabled(False)

        self.imageAdustmentGroupBox = QtWidgets.QGroupBox('Image Adjustment')
        self.imageAdustmentLayout = QtWidgets.QHBoxLayout()
        self.imageAdustmentGroupBox.setLayout(self.imageAdustmentLayout)
        self.imageAdustmentLayout.addWidget(self.imageAdjustmentClahePushButton)
        self.imageAdustmentLayout.addWidget(self.imageAdjustmentClaheClipValueLabel)
        self.imageAdustmentLayout.addWidget(self.imageAdjustmentClaheClipValueDoubleSpinBox)
        self.imageAdustmentLayout.addWidget(self.imageAdjustmentClaheGridLabel)
        self.imageAdustmentLayout.addWidget(self.imageAdjustmentClaheGridValueDoubleSpinBox)
        self.imageAdustmentLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.imageAdustmentLayout.addWidget(self.imageAdjustmentThresholdPushButton)
        self.imageAdustmentLayout.addWidget(self.imageAdjustmentThresholdSlider)
        self.imageAdustmentLayout.addWidget(self.imageAdjustmentThresholdLabel)
        self.VBoxLayout.addWidget(self.imageAdustmentGroupBox)

        self.acquisitionGroupBox = QtWidgets.QGroupBox('Acquisition')
        self.acquisitionLayout = QtWidgets.QHBoxLayout()
        self.acquisitionGroupBox.setLayout(self.acquisitionLayout)
        self.acquisitionLayout.addWidget(self.takeScreenshotPushButton)
        self.acquisitionLayout.addWidget(self.takeVideoPushbutton)
        self.acquisitionLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.VBoxLayout.addWidget(self.acquisitionGroupBox)

        self.image_viewer = ImageViewer()
        self.image_viewer.height()

        # TODO: fix this...
        # self.image_viewer.calibration_signal.connect(self.dmd.calibration_slot)

        self.image_processing = imageProcessor(self.image_viewer.height(), self.image_viewer.width())
        self.image_processing_thread = QThread()
        self.image_processing_thread.start()

        self.image_viewer.resize_event_signal.connect(self.image_processing.resize_slot)
        self.image_viewer.path_signal.connect(self.image_processing.path_slot)
        self.image_viewer.control_signal.connect(self.image_processing.robot_control_slot)
        self.toggle_scale_bar_signal.connect(self.image_viewer.toggle_scale_bar_slot)

        self.set_camera_exposure_signal.connect(self.image_processing.set_exposure_slot)

        self.image_processing.VideoSignal.connect(self.image_viewer.setImage)
        self.image_viewer.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.image_processing.moveToThread(self.image_processing_thread)

        self.image_viewer.click_event_signal.connect(self.handle_click)

        self.VBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        self.HBoxLayout.addLayout(self.VBoxLayout)
        self.HBoxLayout.addWidget(self.image_viewer)


    def initialize_gui_state(self):
        # get the initial state and make the GUI synced to it
        try:
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
        except:
            logging.critical('no connection to microscope, disabling controls')
            self.microscopeGroupBox.setEnabled(False)

        xy_vel = self.stage.get_xy_vel()
        self.stageXYSpeedDoubleSpinBox.setValue(xy_vel)
        self.stageXYSpeedDoubleSpinBox.valueChanged.connect(self.stage.set_xy_vel)
        xy_start_accel, xy_stop_accel = self.stage.get_xy_accels()
        self.stageXYStartAccelerationDoubleSpinBox.setValue(xy_start_accel)
        self.stageXYStopAccelerationDoubleSpinBox.setValue(xy_stop_accel)
        self.stageXYStopAccelerationDoubleSpinBox.valueChanged.connect(self.stage.set_xy_stop_accel)
        self.stageXYStartAccelerationDoubleSpinBox.valueChanged.connect(self.stage.set_xy_start_accel)

        # connect all of our control signals
        self.takeScreenshotPushButton.clicked.connect(self.image_processing.take_screenshot_slot)
        self.start_record_video_signal.connect(self.image_processing.start_recording_video_slot)
        self.stop_record_video_signal.connect(self.image_processing.stop_video_slot)
        self.takeVideoPushbutton.clicked.connect(self.toggleVideoRecording)

        self.magnificationComboBoxWidget.currentTextChanged.connect(self.changeMagnification)
        self.xystageStepSizeDoubleSpinBox.valueChanged.connect(self.stage.set_xystep_size)
        self.zstageStepSizeDoubleSpinBox.valueChanged.connect(self.microscope.set_zstep_size)
        self.filterComboBoxWidget.currentTextChanged.connect(self.changeFilter)
        self.diaShutterPushButton.clicked.connect(self.toggleDiaShutter)
        self.diaLightPushbutton.clicked.connect(self.toggleDiaLamp)
        self.diaVoltageDoubleSpinBox.valueChanged.connect(self.microscope.set_dia_voltage)
        self.cameraExposureDoubleSpinBox.valueChanged.connect(self.setCameraExposure)
        self.scaleBarTogglePushButton.clicked.connect(self.toggleScaleBar)

        self.fgOutputTogglePushButton.clicked.connect(self.toggleFgOutput)
        self.setFunctionGeneratorPushButton.clicked.connect(self.setFunctionGenerator)
        self.pulsePushButton.clicked.connect(self.execute_pulse)
        self.fluorescenceIntensityDoubleSpinBox.valueChanged.connect(self.fluorescence_controller.change_intensity)
        self.fluorescenceToggleLampPushButton.clicked.connect(self.toggleFluorescenceLamp)
        self.fluorescenceShutterPushButton.clicked.connect(self.toggleFluorShutter)
        self.pumpAmountRadioButton.clicked.connect(self.startAmountDispenseMode)
        self.pumpTimeRadioButton.clicked.connect(self.startTimeDispenseMode)
        self.pumpDispensePushButton.clicked.connect(self.pumpDispense)
        self.pumpWithdrawPushButton.clicked.connect(self.pumpWithdraw)
        self.pumpStopPushButton.clicked.connect(self.pump.halt)
        self.pumpTimeRadioButton.click()

        self.drawPathsPushButton.clicked.connect(self.toggleDrawPaths)
        self.detectRobotsPushButton.clicked.connect(self.toggle_robot_detection)
        self.dilationSizeDoubleSpinBox.valueChanged.connect(self.update_detection_params)
        self.bufferSizeDoubleSpinBox.valueChanged.connect(self.update_detection_params)
        self.update_detection_params_signal.connect(self.image_processing.update_detection_params_slot)
        self.enable_robot_detection_signal.connect(self.image_processing.toggle_detection_slot)
        self.oetClearOverlayPushButton.clicked.connect(self.image_processing.clear_paths_overlay_slot)

        self.oetCalibratePushButton.clicked.connect(self.calibrate_dmd)
        self.oetClearPushButton.clicked.connect(self.clear_dmd)
        self.oetProjectCirclePushButton.clicked.connect(self.toggle_project_circle)
        self.oetLoadProjectionImagePushButton.clicked.connect(self.load_oet_projection)
        self.oetProjectImagePushButton.clicked.connect(self.toggle_project_image)
        self.oetControlProjectionsPushButton.clicked.connect(self.toggle_controL_projections)
        self.oetProjectDetectionPushButton.clicked.connect(self.project_detection_pattern)
        self.oetOpenRobotsPushButton.clicked.connect(self.update_detection_params)
        self.oetControlDetectedPushButton.clicked.connect(self.toggleControlDetected)
        self.oetScaleUpPushButton.clicked.connect(self.scale_up_oet_projection)
        self.oetToggleLampPushButton.clicked.connect(self.toggle_dmd_lamp)
        if self.dmd != False:
            self.oetLampIntesnsityDoubleSpinBox.valueChanged.connect(self.dmd.set_dmd_current)

        self.image_viewer.enable_dmd_signal.connect(self.enable_dmd_controls)
        self.image_processing.fps_signal.connect(self.fps_slot)

        self.imageAdjustmentClaheClipValueDoubleSpinBox.valueChanged.connect(self.apply_image_adjustment)
        self.imageAdjustmentClaheGridValueDoubleSpinBox.valueChanged.connect(self.apply_image_adjustment)
        self.imageAdjustmentClahePushButton.clicked.connect(self.apply_image_adjustment)
        self.clahe_params_signal.connect(self.image_processing.clay_params_slot)
        self.imageAdjustmentThresholdSlider.valueChanged.connect(self.handle_image_threshold_slider)


        self.oetProjectCirclePushButton.setEnabled(False)
        self.oetLoadProjectionImagePushButton.setEnabled(False)
        self.oetProjectImagePushButton.setEnabled(False)
        self.oetControlProjectionsPushButton.setEnabled(False)
        self.oetScaleDoubleSpinBox.setEnabled(False)
        self.oetRotationDoubleSpinBox.setEnabled(False)
        self.oetTranslateDoubleSpinBox.setEnabled(False)
        self.oetScaleUpPushButton.setEnabled(False)
        self.oetProjectDetectionPushButton.setEnabled(False)
        self.oetOpenRobotsPushButton.setEnabled(False)
        self.oetControlDetectedPushButton.setEnabled(False)

        if self.dmd != False:
            self.dmd.initialize_dmd()
        try:
            self.fluorescence_controller.turn_all_off()
        except:
            logging.critical('fluorescence controller not connected, disabling controls')
            self.fluorescenceGroupBox.setEnabled(False)



    @QtCore.pyqtSlot()
    def enable_dmd_controls(self):
        self.oetProjectCirclePushButton.setEnabled(True)
        self.oetLoadProjectionImagePushButton.setEnabled(True)
        self.oetProjectDetectionPushButton.setEnabled(True)
        self.oetOpenRobotsPushButton.setEnabled(True)
        self.oetControlDetectedPushButton.setEnabled(True)

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


class ImageViewer(QtWidgets.QWidget):
    resize_event_signal = QtCore.pyqtSignal(QtCore.QSize, 'PyQt_PyObject')
    click_event_signal = QtCore.pyqtSignal(QtGui.QMouseEvent)
    path_signal = QtCore.pyqtSignal('PyQt_PyObject')
    control_signal = QtCore.pyqtSignal('PyQt_PyObject')
    calibration_signal = QtCore.pyqtSignal('PyQt_PyObject')
    enable_dmd_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.image = QtGui.QImage()
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
        self.ignore_release = True
        self.drawing_path = False
        self.calibrating = False
        self.robot_paths = []
        self.path_payload = {}
        self.calibration_payload = []
        self.begin_path = None
        self.controlling_detected = False
        self.scale_bar_shown = False
        self.scale_bar_values = {'2x': ['500um', 162],
                                 '4x': ['200um', 125],
                                 '10x': ['100um', 156],
                                 '20x': ['50um', 152],
                                 '40x': ['10um', 63]}
        self.scale_bar_value = 'Unk'
        self.scale_bar_length = 10

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        # draw in the center here
        x = int(self.width() / 2 - self.image.width() / 2)  # offset to draw in center
        painter.drawImage(x, 0, self.image)
        self.image = QtGui.QImage()

    # @QtCore.pyqtSlot(QtGui.QImage)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def toggle_scale_bar_slot(self, objective):
        self.scale_bar_shown = not self.scale_bar_shown
        self.scale_bar_value = self.scale_bar_values[objective][0]
        self.scale_bar_length = self.scale_bar_values[objective][1]

    @QtCore.pyqtSlot('PyQt_PyObject')
    def setImage(self, np_img):
        if self.scale_bar_shown:
            # draw our scale line and text in a reasonable location
            cv2.putText(np_img, self.scale_bar_value,
                        (20, int(self.height() * .925)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        255,
                        2)
            # draw it three times to get over the stupid end cap business...
            cv2.line(np_img, (20, int(self.height() * .925) + 20),
                     (self.scale_bar_length, int(self.height() * .925) + 20),
                     255, 1)
            cv2.line(np_img, (20, int(self.height() * .925) + 21),
                     (self.scale_bar_length, int(self.height() * .925) + 21),
                     255, 1)
            cv2.line(np_img, (20, int(self.height() * .925) + 22),
                     (self.scale_bar_length, int(self.height() * .925) + 22),
                     255, 1)
        if len(np_img.shape) > 2:
            # Format_RGB16
            qt_img = qimage2ndarray.array2qimage(np_img)
            self.image = qt_img
        else:
            self.image = QtGui.QImage(np_img.data, self.height(), self.width(), np_img.strides[0],
                                      QtGui.QImage.Format_Grayscale8)

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
        if self.drawing_path:
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
        if self.drawing_path:
            self.begin_path = event.pos()
        elif self.calibrating:
            # just scale this one here...probably could be neater
            x_scaled = event.pos().x() / self.width()
            y_scaled = event.pos().y() / self.height()
            self.calibration_payload.append((x_scaled, y_scaled))
            string = f'calibration point marked: {x_scaled}, {y_scaled}'
            logging.info(string)
            if len(self.calibration_payload) > 2:
                QtWidgets.QMessageBox.about(self, 'Calibration', 'Calibration Complete')
                self.calibrating = False
                self.enable_dmd_signal.emit()
        elif self.controlling_detected:
            offset = (self.width() - self.image_width) // 2
            self.path_payload['start_x'] = event.pos().x() - offset
            self.path_payload['start_y'] = event.pos().y()
            self.control_signal.emit(copy.deepcopy(self.path_payload))
