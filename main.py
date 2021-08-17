import sys

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

        self.dispenseMode = None
        self.project_circle_mode = False
        self.project_image_mode = False

        self.setupUI(self)
        self.initialize_gui_state()
        self.showMaximized()

        # connect to the video thread and start the video
        self.start_video_signal.connect(self.image_processing.startVideo)
        self.setChildrenFocusPolicy(QtCore.Qt.ClickFocus)
        self.start_video_signal.emit()

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
        # now we want to project 3 circles on the dmd for the user to click so that we can calibrate
        QtWidgets.QMessageBox.about(self, 'Calibration',
                                    'Please click the center of the 3 (clipped) projected circles in a CLOCKWISE \
                                    fashion to calibrate the DMD.')
        self.dmd.project_calibration_image()
        self.image_viewer.calibration_payload = []
        self.image_viewer.calibrating = True

    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def handle_click(self, event):
        # see if we are calibrated
        if len(self.image_viewer.calibration_payload) < 3:
            return
        x = event.pos().x()
        y = event.pos().y()

        # scale everything
        unit_scaled_viewer_x = x / self.image_viewer.width()
        unit_scaled_viewer_y = y / self.image_viewer.height()

        # check if we can illuminate the clicked area with the dmd
        check = self.check_if_in_dmd_area(unit_scaled_viewer_x, unit_scaled_viewer_y)
        if not check:
            print('not within DMD area. ignoring click')
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
        elif self.project_image_mode:
            self.dmd.project_loaded_image(dmd_scaled_x, dmd_scaled_y)

    def run_oet_commands(self):
        if self.detectRobotsPushButton.isChecked():
            self.detectRobotsPushButton.click()

        # grab our current controlled robots, project a control dmd image around them, and stop detection
        img = self.image_processing.robot_control_mask

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

    def camera_to_dmd_conversion(self, camera_view):
        # takes a camera image as input and maps it to the DMD projector. TODO: MOVE TO IMAGE PROCESSOR
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
        self.image_processing.rotation = state

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
