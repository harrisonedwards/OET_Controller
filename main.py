import sys
import names
import PyQt5.QtGui
from PyQt5 import QtCore, QtGui, QtWidgets
from function_generator import FunctionGenerator
from pump import Pump
from microscope import Microscope
from fluorescence_controller import FluorescenceController
from stage import Stage
from mightex import Polygon1000
import cv2
import matplotlib.pyplot as plt
import numpy as np
from GUI import GUI


class Window(GUI):
    start_video_signal = QtCore.pyqtSignal()
    set_camera_exposure_signal = QtCore.pyqtSignal('PyQt_PyObject')
    screenshot_signal = QtCore.pyqtSignal()
    start_record_video_signal = QtCore.pyqtSignal()
    stop_record_video_signal = QtCore.pyqtSignal()
    enable_robot_detection_signal = QtCore.pyqtSignal('PyQt_PyObject')
    update_detection_params_signal = QtCore.pyqtSignal('PyQt_PyObject')
    clahe_params_signal = QtCore.pyqtSignal('PyQt_PyObject')

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

        self.dispenseMode = None  # should be set by the GUI immediately
        self.project_circle_mode = False
        self.project_image_mode = False
        self.robots = {}
        self.projection_image = None

        self.setupUI(self)
        self.initialize_gui_state()
        self.showMaximized()

        self.image_processing.robot_signal.connect(self.robot_control_slot)

        # connect to the video thread and start the video
        self.start_video_signal.connect(self.image_processing.startVideo)
        self.setChildrenFocusPolicy(QtCore.Qt.ClickFocus)
        self.start_video_signal.emit()

        # make our image processor aware of the system state
        self.update_detection_params()

    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def handle_click(self, event):
        # see if we are calibrated
        if len(self.image_viewer.calibration_payload) < 3:
            print('not calibrated...ignoring click')
            return
        x = event.pos().x()
        y = event.pos().y()

        # scale everything
        unit_scaled_viewer_x = x / self.image_viewer.width()
        unit_scaled_viewer_y = y / self.image_viewer.height()

        # check if we can illuminate the clicked area with the dmd
        check = self.check_if_in_dmd_area(unit_scaled_viewer_x, unit_scaled_viewer_y)
        if not check:
            print('not within DMD area...ignoring click')
            return

        # get the full scale of our dmd area
        dmd_fs_x = self.image_viewer.calibration_payload[-1][0] - self.image_viewer.calibration_payload[0][0]
        dmd_fs_y = self.image_viewer.calibration_payload[-1][1] - self.image_viewer.calibration_payload[0][1]

        # subtract out our top left calibration spot and divide by full scale
        dmd_scaled_x = (unit_scaled_viewer_x - self.image_viewer.calibration_payload[0][0]) / dmd_fs_x
        dmd_scaled_y = (unit_scaled_viewer_y - self.image_viewer.calibration_payload[0][1]) / dmd_fs_y

        # project in the proper mode
        if self.project_circle_mode:
            self.dmd.project_circle(dmd_scaled_x, dmd_scaled_y)
            self.dmd.update()
        elif self.project_image_mode == 'adding_robots':
            cx, cy, angle = self.dmd.project_loaded_image(dmd_scaled_x, dmd_scaled_y, 0,
                                                          self.projection_image, adding=True)
            name = names.get_first_name()
            while name in self.robots:
                name = names.get_first_name()
            checkbox = QtWidgets.QCheckBox(name)
            self.robots[name] = {'cx': cx, 'cy': cy, 'angle': angle,
                                 'checkbox': checkbox, 'image': np.copy(self.projection_image),
                                 'scale': 100}
            self.oetRobotsLayout.addWidget(checkbox)
            self.oetRobotsEmptyLabel.setVisible(False)
            self.dmd.update()
        # elif self.project_image_mode == 'controlling_robots':
        #     self.dmd.project_loaded_image(dmd_scaled_x, dmd_scaled_y, adding_only=False)

    def handle_robot_movement(self, key):
        adding = 0
        for robot in self.robots:
            if self.robots[robot]['checkbox'].isChecked():
                rotate_amt = self.oetRotationDoubleSpinBox.value()
                translate_amt = self.oetTranslateDoubleSpinBox.value()
            else:
                rotate_amt, translate_amt = 0, 0
            if key == QtCore.Qt.Key_W:
                cx, cy, angle = self.dmd.translate(-translate_amt,
                                                   self.robots[robot]['cx'],
                                                   self.robots[robot]['cy'],
                                                   self.robots[robot]['angle'],
                                                   self.robots[robot]['scale'],
                                                   self.robots[robot]['image'],
                                                   adding=adding)
            elif key == QtCore.Qt.Key_S:
                cx, cy, angle = self.dmd.translate(translate_amt,
                                                   self.robots[robot]['cx'],
                                                   self.robots[robot]['cy'],
                                                   self.robots[robot]['angle'],
                                                   self.robots[robot]['scale'],
                                                   self.robots[robot]['image'],
                                                   adding=adding)
            elif key == QtCore.Qt.Key_A:
                cx, cy, angle = self.dmd.strafe(translate_amt,
                                                self.robots[robot]['cx'],
                                                self.robots[robot]['cy'],
                                                self.robots[robot]['angle'],
                                                self.robots[robot]['scale'],
                                                self.robots[robot]['image'],
                                                adding=adding)
            elif key == QtCore.Qt.Key_D:
                cx, cy, angle = self.dmd.strafe(-translate_amt,
                                                self.robots[robot]['cx'],
                                                self.robots[robot]['cy'],
                                                self.robots[robot]['angle'],
                                                self.robots[robot]['scale'],
                                                self.robots[robot]['image'],
                                                adding=adding)
            elif key == QtCore.Qt.Key_Q:
                cx, cy, angle = self.dmd.turn_robot(rotate_amt,
                                                    self.robots[robot]['cx'],
                                                    self.robots[robot]['cy'],
                                                    self.robots[robot]['angle'],
                                                    self.robots[robot]['scale'],
                                                    self.robots[robot]['image'],
                                                    adding=adding)
            elif key == QtCore.Qt.Key_E:
                cx, cy, angle = self.dmd.turn_robot(-rotate_amt,
                                                    self.robots[robot]['cx'],
                                                    self.robots[robot]['cy'],
                                                    self.robots[robot]['angle'],
                                                    self.robots[robot]['scale'],
                                                    self.robots[robot]['image'],
                                                    adding=adding)
            adding += 1
            self.robots[robot]['cx'] = cx
            self.robots[robot]['cy'] = cy
            self.robots[robot]['angle'] = angle
        self.dmd.update()

    def scale_up_oet_projection(self):
        adding = 0
        for robot in self.robots:
            if self.robots[robot]['checkbox'].isChecked():
                scale_amt = self.oetScaleDoubleSpinBox.value()
            else:
                scale_amt = 0
            scale = self.dmd.scale_projection(scale_amt,
                                              self.robots[robot]['cx'],
                                              self.robots[robot]['cy'],
                                              self.robots[robot]['angle'],
                                              self.robots[robot]['scale'],
                                              self.robots[robot]['image'],
                                              adding=adding)
            self.robots[robot]['scale'] = scale
            adding += 1
        self.dmd.update()

    def clear_dmd(self):
        # add all robot clearing
        for robot in self.robots:
            checkbox = self.robots[robot]['checkbox']
            self.oetRobotsLayout.removeWidget(checkbox)
            checkbox.deleteLater()
            checkbox = None
        self.robots = {}
        self.dmd.clear_oet_projection()
        self.oetClearPushButton.setChecked(False)

    def toggle_project_image(self):
        if self.oetProjectImagePushButton.isChecked():
            self.project_image_mode = 'adding_robots'
            self.oetRobotsGroupBox.setEnabled(False)
            self.oetProjectCirclePushButton.setChecked(False)
            self.oetControlProjectionsPushButton.setChecked(False)
            self.project_circle_mode = False
        elif not self.oetProjectImagePushButton.isChecked():
            self.oetControlProjectionsPushButton.setEnabled(True)

    def toggle_controL_projections(self):
        if self.oetControlProjectionsPushButton.isChecked():
            self.project_image_mode = 'controlling_robots'
            self.oetRobotsGroupBox.setEnabled(True)
            self.oetProjectImagePushButton.setChecked(False)
            self.oetProjectCirclePushButton.setChecked(False)
            self.project_circle_mode = False
            self.oetScaleDoubleSpinBox.setEnabled(True)
            self.oetScaleUpPushButton.setEnabled(True)
            self.oetRotationDoubleSpinBox.setEnabled(True)
            self.oetTranslateDoubleSpinBox.setEnabled(True)

    def toggle_project_circle(self):
        self.project_circle_mode = self.oetProjectCirclePushButton.isChecked()
        self.oetProjectImagePushButton.setChecked(False)
        self.oetControlProjectionsPushButton.setChecked(False)
        self.project_image_mode = False

    def project_detection_pattern(self):
        # TODO: move to image processor
        if self.detectRobotsPushButton.isChecked():
            self.detectRobotsPushButton.click()

        # grab our current controlled robots, project a control dmd image around them, and stop detection
        img = self.image_processing.detection_overlay

        # resize to our viewer window image size
        img = cv2.resize(img, (self.image_viewer.height() * 2060 // 2048, self.image_viewer.height()))
        _, img = cv2.threshold(img, 10, 255, cv2.THRESH_BINARY)

        # now we crop out the sections that cannot be illuminated by the dmd
        # need an offset (difference between image width and viewer width)
        offset = int(0.5 * (self.image_viewer.width() - img.shape[0]))
        dmd_start_x = int(self.image_viewer.calibration_payload[0][0] * self.image_viewer.width() - offset)
        dmd_end_x = int(self.image_viewer.calibration_payload[-1][0] * self.image_viewer.width() - offset)
        dmd_start_y = int(self.image_viewer.calibration_payload[0][1] * self.image_viewer.height())
        dmd_end_y = int(self.image_viewer.calibration_payload[-1][1] * self.image_viewer.height())
        img = img[dmd_start_y:dmd_end_y, dmd_start_x:dmd_end_x]

        # final resize to adjust to exact dimensions for dmd projection
        img = cv2.resize(img, (912 * 2, 1140))
        _, img = cv2.threshold(img, 10, 255, cv2.THRESH_BINARY)

        # finally, render it
        print('rendering to dmd...')
        self.dmd.render_to_dmd(img)

    def apply_image_adjustment(self, value):
        clip = self.imageAdjustmentClaheClipValueDoubleSpinBox.value()
        grid = self.imageAdjustmentClaheGridValueDoubleSpinBox.value()
        status = self.imageAdjustmentClahePushButton.isChecked()
        print(f'clahe: {status}, {clip}, {grid}')
        clahe_values = {'status': status, 'clip': clip, 'grid': grid}
        self.clahe_params_signal.emit(clahe_values)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def robot_control_slot(self, robot_signal):
        print(robot_signal)
        cx, cy, robot = robot_signal

    def toggle_robot_detection(self):
        state = self.detectRobotsPushButton.isChecked()
        self.enable_robot_detection_signal.emit(state)

    def toggleVideoRecording(self):
        state = self.takeVideoPushbutton.isChecked()
        if state:
            self.start_record_video_signal.emit()
        else:
            self.stop_record_video_signal.emit()

    def toggleFluorescenceLamp(self):
        state = self.fluorescenceToggleLampPushButton.isChecked()
        if state:
            self.fluorescence_controller.turn_led_on()
        else:
            self.fluorescence_controller.turn_all_off()

    def toggle_dmd_lamp(self):
        state = self.oetToggleLampPushButton.isChecked()
        self.dmd.toggle_dmd_light(state)

    def load_oet_projection(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file for projection')
        if file_name != '':
            self.load_projection_image(file_name)
            self.oetProjectImagePushButton.setEnabled(True)

    def load_projection_image(self, file_name):
        projection_image = cv2.imread(file_name)
        print(f'loaded image of size {projection_image.shape}')

        # convert to grayscale and binarize
        projection_image = cv2.cvtColor(projection_image, cv2.COLOR_BGR2GRAY)
        ret, projection_image = cv2.threshold(projection_image, 127, 255, cv2.THRESH_BINARY)
        print(f'image converted to binary. shape: {projection_image.shape}')
        self.projection_image = np.copy(projection_image)

    def calibrate_dmd(self):
        print('calibrating dmd...')
        # now we want to project 3 circles on the dmd for the user to click so that we can calibrate
        QtWidgets.QMessageBox.about(self, 'Calibration',
                                    'Please click the center of the 3 (clipped) projected circles in a CLOCKWISE \
                                    fashion to calibrate the DMD. Ensure that the DMD Lamp is on and visible.')
        self.dmd.project_calibration_image()
        self.image_viewer.calibration_payload = []
        self.image_viewer.calibrating = True

    def update_detection_params(self):
        params_dict = {'buffer_size': int(self.bufferSizeDoubleSpinBox.value()),
                       'dilation_size': int(self.dilationSizeDoubleSpinBox.value()),
                       'objective': self.magnificationComboBoxWidget.currentText(),
                       'open_robots': self.oetOpenRobotsPushButton.isChecked()}
        self.update_detection_params_signal.emit(params_dict)

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

    def toggleDrawPaths(self):
        state = self.drawPathsPushButton.isChecked()
        self.image_viewer.drawing_path = state

    def toggleControlDetected(self):
        self.image_viewer.controlling_detected = self.oetControlDetectedPushButton.isChecked()

    def closeEvent(self, event):
        print('closing all connections...')
        for hardware in [self.microscope, self.fluorescence_controller, self.function_generator,
                         self.dmd, self.pump]:
            if hardware is not False:
                hardware.__del__()

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            self.stage.halt()
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
            return
        elif key == QtCore.Qt.Key_PageDown:
            self.microscope.move_rel_z(-self.zstageStepSizeDoubleSpinBox.value())
            return
        if self.project_image_mode:
            self.handle_robot_movement(key)

    def keyReleaseEvent(self, event):
        pass

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
        if self.detectRobotsPushButton.isChecked():
            self.detectRobotsPushButton.click()
        idx_dict = {k: v for k, v in zip(self.objectives, range(1, 7))}
        self.microscope.set_objective(idx_dict[text])
        self.update_detection_params()

    def changeFilter(self, text):
        idx_dict = {k: v for k, v in zip(self.filter_positions, range(1, 7))}
        self.microscope.set_filter(idx_dict[text])

    def toggleFluorShutter(self):
        state = self.fluorescenceShutterPushButton.isChecked()
        self.microscope.set_turret_shutter(state)

    def toggleDiaShutter(self):
        state = self.diaShutterPushButton.isChecked()
        self.microscope.set_dia_shutter(state)

    def toggleDiaLamp(self):
        state = self.diaLightPushbutton.isChecked()
        self.microscope.toggle_dia_light(state)

    def setCameraExposure(self, exposure):
        self.set_camera_exposure_signal.emit(exposure)


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
