import logging, time, sys, os
import pickle
from time import strftime

import detection

log_name = strftime('..\\logs\\%Y_%m_%d_%H_%M_%S.log', time.gmtime())
logging.basicConfig(filename=log_name, level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
# logging.getLogger().addHandler(logging.Formatter(fmt=' %(name)s :: %(levelname)-8s :: %(message)s'.replace('\n', '')))
# from inputs import get_gamepad
import names, re
import PyQt5.QtGui
from PyQt5 import QtCore, QtGui, QtWidgets, QtTest
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
import threading


class Window(GUI):
    start_video_signal = QtCore.pyqtSignal()
    set_camera_exposure_signal = QtCore.pyqtSignal('PyQt_PyObject')
    screenshot_signal = QtCore.pyqtSignal()
    start_record_video_signal = QtCore.pyqtSignal()
    stop_record_video_signal = QtCore.pyqtSignal()
    enable_robot_detection_signal = QtCore.pyqtSignal('PyQt_PyObject')
    enable_cell_detection_signal = QtCore.pyqtSignal('PyQt_PyObject')
    update_detection_params_signal = QtCore.pyqtSignal('PyQt_PyObject')
    image_adjustment_params_signal = QtCore.pyqtSignal('PyQt_PyObject')
    toggle_scale_bar_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self):
        super(Window, self).__init__()
        self.unavailable_instruments = []
        self.dmd = False
        self.unavailable_instruments.append('DMD')
        try:
            # raise Exception('test')
            dmd_start_thread = threading.Thread(target=self.start_dmd)
            dmd_start_thread.start()
        except Exception as e:
            logging.warning(f'unable to connect to polygon: {e}')
            self.dmd = False
            self.unavailable_instruments.append('DMD')

        try:
            self.function_generator = FunctionGenerator()
        except Exception as e:
            logging.CRITICAL(f'Function generator control not available: {e}')
            self.function_generator = False
            self.unavailable_instruments.append('function generator')

        try:
            self.pump = Pump()
        except Exception as e:
            logging.CRITICAL(f'Pump control not available: {e}')
            self.pump = False
            self.unavailable_instruments.append('pump')

        try:
            self.fluorescence_controller = FluorescenceController()
        except Exception as e:
            logging.CRITICAL(f'Fluorescence control not available: {e}')
            self.fluorescence_controller = False
            self.unavailable_instruments.append('fluorescence')

        try:
            self.stage = Stage()
        except Exception as e:
            logging.CRITICAL(f'Stage not available: {e}')
            self.stage = False
            self.unavailable_instruments.append('stage')

        try:
            self.microscope = Microscope()
        except Exception as e:
            logging.CRITICAL(f'Microscope control not available: {e}')
            self.microscope = False
            self.unavailable_instruments.append('microscope')

        self.dispenseMode = None  # should be set by the GUI immediately
        self.project_circle_mode = False
        self.project_image_mode = False
        self.project_eraser_mode = False
        self.robots = {}
        self.projection_image = None
        self.fps = 0
        self.stage_pos = (0, 0)
        self.pump_status = ''
        self.detection_model_loc = r'C:\Users\Mohamed\Desktop\Harrison\OET\cnn_models' \
                                   r'\8515_vaL_model_augmented_w_gfp_class_weighted2 '
        self.default_directory = r'C:\Users\Mohamed\Desktop\Harrison'
        self.gui_update_thread = threading.Thread(target=self.get_system_position, daemon=True)

        if self.dmd:
            dmd_start_thread.join()
        self.setupUI(self)
        self.initialize_gui_state()

        self.image_processing.robot_signal.connect(self.robot_control_slot)

        # connect to the video thread and start the video
        self.start_video_signal.connect(self.image_processing.startVideo)
        self.setChildrenFocusPolicy(QtCore.Qt.ClickFocus)
        self.start_video_signal.emit()

        # make our image processor aware of the system state
        self.update_detection_params()
        self.showMaximized()
        self.gui_update_thread.start()

    def start_dmd(self):
        self.dmd = Polygon1000(1140, 912)

    def toggle_fg_sweep(self):
        state = self.sweepPushButton.isChecked()
        start = self.sweepStartDoubleSpinBox.value() * 1000
        stop = self.sweepStopDoubleSpinBox.value() * 1000
        time = self.sweepTimeDoubleSpinBox.value()
        self.function_generator.toggle_sweep(state, start, stop, time)

    def get_system_position(self):
        while True:
            try:
                pos = self.stage.get_position()
                x, y = pos.decode().split(' ')[0], pos.decode().split(' ')[1]
                self.stage_pos = (x, y)

                if self.pump.ser is not None:
                    self.pump_status = self.pump.get_pump_status()
                else:
                    self.pump_status = 'disconnected'

                time.sleep(.1)
            except Exception as e:
                logging.info(f'minor error encountered when communicating with system: {e}')
        # response = self.microscope.get_z()
        # z = float(response.iZPOSITION)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def fps_slot(self, fps):
        self.fps = float(fps)
        x, y = self.stage_pos

        spacer = ' ' * 20
        self.statusBar.showMessage(f'Controls: Arrows->XY, PageU/D->Z, ESC->HALT, Space->FG ON/OFF, WASD->Robot Move'
                                   f'{spacer}FPS: {fps:.2f}{spacer}POSITION: {x}mm, {y}mm{spacer}'
                                   f'PUMP: {self.pump_status}{spacer} DETECTOR: {self.detection_model_loc}')

    def bookmark_current_location(self):
        x, y = self.stage_pos
        index = self.xyBookMarkComboBox.count() + 1
        bookmark_string = f'{index}:  {x}mm, {y}mm'
        self.xyBookMarkComboBox.addItem(bookmark_string)
        self.xyBookMarkComboBox.setCurrentIndex(index - 1)
        if self.xyBookMarkComboBox.count() == 1:
            self.xyBookMarkComboBox.currentIndexChanged.connect(self.move_to_bookmarked_location)

    def move_to_bookmarked_location(self, index):
        bookmark = self.xyBookMarkComboBox.currentText()
        if self.xyBookMarkComboBox.count() != 0:
            x = float(re.search(': (.+?)mm', bookmark).group(1))
            y = float(re.search('mm, (.+?)mm', bookmark).group(1))
            self.stage.move_absolute(x, y)

    def go_to_current_bookmark(self):
        self.move_to_bookmarked_location(-1)

    def set_optical_config(self, text):
        if self.opticalConfigComboBox.currentText() == 'New':
            return
        logging.info(f'setting optical config to: {text}')
        config = f'C:\\Users\\Mohamed\\Desktop\\Harrison\\OET\\configs\\{text}'
        fluorescence_intensity, fluorescence_state, exposure, status = pickle.load(open(config, 'rb'))
        self.fluorescenceIntensityDoubleSpinBox.setValue(fluorescence_intensity)
        self.fluorescenceShutterPushButton.setChecked(fluorescence_state)
        self.cameraExposureDoubleSpinBox.setValue(exposure)
        self.microscope.load_config(status)
        self.microscope.get_status()
        self.update_gui_state(loading=True)
        # TODO: need to set xylis configs and exposure

    def go_to_current_optical_config(self):
        text = self.opticalConfigComboBox.currentText()
        self.set_optical_config(text)
        print('going to config...')

    def clear_current_optical_config(self):
        config = self.opticalConfigComboBox.currentText()
        reply = QtWidgets.QMessageBox.question(self, 'Overwrite', f'Are you sure you want to overwrite {config}?',
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            logging.info(f'clearing optical config{config}')
            print(f'clearing optical config: {config}')
            index = self.opticalConfigComboBox.currentIndex()
            self.opticalConfigComboBox.setCurrentText('New')
            self.opticalConfigComboBox.removeItem(index)
            os.remove(f'C:\\Users\\Mohamed\\Desktop\\Harrison\\OET\\configs\\{config}')
        else:
            print(f'not removing {config}')
            return

    def save_optical_config(self):
        print('saving config...')
        status = self.microscope.get_status()
        fluorescence_intensity = self.fluorescenceIntensityDoubleSpinBox.value()
        fluorescence_state = self.fluorescenceShutterPushButton.isChecked()
        exposure = self.cameraExposureDoubleSpinBox.value()
        save_config = [fluorescence_intensity, fluorescence_state, exposure, status]
        if self.opticalConfigComboBox.currentText() == 'New':
            name, ok = QtWidgets.QInputDialog.getText(self, 'Name new config', 'Enter configuration name:')
            if not ok:
                return
            with open(f'C:\\Users\\Mohamed\\Desktop\\Harrison\\OET\\configs\\{name}_config.p', 'wb+') as f:
                pickle.dump(save_config, f)
            self.opticalConfigComboBox.addItem(f'{name}_config.p')
            self.opticalConfigComboBox.setCurrentText(f'{name}_config.p')
            print(f'wrote new configuration: {name}')
        else:
            config = self.opticalConfigComboBox.currentText()
            reply = QtWidgets.QMessageBox.question(self, 'Overwrite', f'Are you sure you want to overwrite {config}?',
                                         QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                with open(f'C:\\Users\\Mohamed\\Desktop\\Harrison\\OET\\configs\\{config}', 'wb+') as f:
                    pickle.dump(save_config, f)
                print(f'overwriting config: {config}')
            else:
                print('not saving config')
                return

    def change_condenser_position(self, index):
        index += 1
        logging.info(f'changing condenser position:f{index}')
        self.microscope.set_condenser_position(index)

    def update_condenser_aperture(self, value):
        logging.info(f'setting condenser aperture: {value}')
        self.condenserApertureLabel.setText(f'Aperture:{value}mm')
        self.microscope.set_aperture(value)

    def update_condenser_field_stop(self, value):
        logging.info(f'setting condenser field stop: {value}')
        self.condenserFieldStopLabel.setText(f'Field Stop:{value}mm')
        self.microscope.set_field_stop(value)

    def execute_pulse(self):
        duration = self.pulseDoubleSpinBox.value()
        if self.fgOutputTogglePushButton.isChecked():
            self.fgOutputTogglePushButton.click()
        self.fgOutputTogglePushButton.click()
        QtTest.QTest.qWait(duration)
        self.fgOutputTogglePushButton.click()

    def get_scaled_position(self, event):
        x = event.pos().x()
        y = event.pos().y()

        # scale everything
        unit_scaled_viewer_x = x / self.image_viewer.width()
        unit_scaled_viewer_y = y / self.image_viewer.height()

        # see if we are calibrated
        if len(self.image_viewer.calibration_payload) < 2:
            logging.info('not within DMD area...unable to render')
            return -1, -1

        # check if we can illuminate the clicked area with the dmd
        check = self.check_if_in_dmd_area(unit_scaled_viewer_x, unit_scaled_viewer_y)
        if not check:
            logging.info('not within DMD area...unable to render')
            return -1, -1

        # get the full scale of our dmd area
        dmd_fs_x = self.image_viewer.calibration_payload[-1][0] - self.image_viewer.calibration_payload[0][0]
        dmd_fs_y = self.image_viewer.calibration_payload[-1][1] - self.image_viewer.calibration_payload[0][1]

        # subtract out our top left calibration spot and divide by full scale
        dmd_scaled_x = (unit_scaled_viewer_x - self.image_viewer.calibration_payload[0][0]) / dmd_fs_x
        dmd_scaled_y = (unit_scaled_viewer_y - self.image_viewer.calibration_payload[0][1]) / dmd_fs_y

        return dmd_scaled_x, dmd_scaled_y

    def handle_mouse_down(self, event):
        # see if we are calibrated
        if len(self.image_viewer.calibration_payload) < 2:
            return

        dmd_scaled_x, dmd_scaled_y = self.get_scaled_position(event)

        # project in the proper mode
        if self.project_circle_mode:
            self.dmd.project_brush(dmd_scaled_x, dmd_scaled_y, self.oetBrushRadiusDoubleSpinBox.value())
            self.dmd.update()
        elif self.project_eraser_mode:
            self.dmd.project_eraser(dmd_scaled_x, dmd_scaled_y, self.oetBrushRadiusDoubleSpinBox.value())
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
        self.prev_scaled_x, self.prev_scaled_y = dmd_scaled_x, dmd_scaled_y

    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def handle_mouse_move(self, event):
        dmd_scaled_x, dmd_scaled_y = self.get_scaled_position(event)
        if dmd_scaled_x == -1 or dmd_scaled_y == -1:
            return
        if self.project_circle_mode:
            self.dmd.project_brush(dmd_scaled_x, dmd_scaled_y, self.oetBrushRadiusDoubleSpinBox.value(),
                                   self.prev_scaled_x, self.prev_scaled_y)
            self.dmd.update()
        elif self.project_eraser_mode:
            self.dmd.project_eraser(dmd_scaled_x, dmd_scaled_y, self.oetBrushRadiusDoubleSpinBox.value(),
                                    self.prev_scaled_x, self.prev_scaled_y)
            self.dmd.update()
        self.prev_scaled_x, self.prev_scaled_y = dmd_scaled_x, dmd_scaled_y

    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def handle_click(self, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            self.handle_mouse_down(event)

    def handle_robot_movement(self, key):
        adding = 0
        for robot in self.robots:
            if self.robots[robot]['checkbox'].isChecked() and key in [87, 65, 83, 68, 81, 69]:
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
            if self.robots[robot]['checkbox'].isChecked() and key in [87, 65, 83, 68, 81, 69]:
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
            self.oetObjectsGroupBox.setEnabled(False)
            self.oetProjectCircleBrushPushButton.setChecked(False)
            self.oetControlProjectionsPushButton.setChecked(False)
            self.project_circle_mode = False
        elif not self.oetProjectImagePushButton.isChecked():
            self.oetControlProjectionsPushButton.setEnabled(True)

    def toggle_controL_projections(self):
        if self.oetControlProjectionsPushButton.isChecked():
            self.project_image_mode = 'controlling_robots'
            self.oetObjectsGroupBox.setEnabled(True)
            self.oetProjectImagePushButton.setChecked(False)
            self.oetProjectCircleBrushPushButton.setChecked(False)
            self.project_circle_mode = False
            self.oetScaleDoubleSpinBox.setEnabled(True)
            self.oetScaleUpPushButton.setEnabled(True)
            self.oetRotationDoubleSpinBox.setEnabled(True)
            self.oetTranslateDoubleSpinBox.setEnabled(True)

    def toggle_project_brush(self):
        self.project_circle_mode = self.oetProjectCircleBrushPushButton.isChecked()
        self.oetProjectCircleEraserPushButton.setChecked(False)
        self.project_eraser_mode = False
        self.oetProjectImagePushButton.setChecked(False)
        self.oetControlProjectionsPushButton.setChecked(False)
        self.project_image_mode = False

    def toggle_erase_brush(self):
        self.project_eraser_mode = self.oetProjectCircleEraserPushButton.isChecked()
        self.oetProjectCircleBrushPushButton.setChecked(False)
        self.project_circle_mode = False
        self.oetProjectImagePushButton.setChecked(False)
        self.oetControlProjectionsPushButton.setChecked(False)
        self.project_image_mode = False

    def project_detection_pattern(self):
        # TODO: move to image processor
        if self.detectRobotsPushButton.isChecked():
            self.detectRobotsPushButton.click()

        # grab our current controlled robots, project a control dmd image around them, and stop detection
        # img = self.image_processing.detection_overlay

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
        logging.info('rendering to dmd...')
        self.dmd.render_to_dmd(img)

    def apply_image_adjustment(self, value):

        clahe = self.imageAdjustmentClahePushButton.isChecked()
        clip = self.imageAdjustmentClaheClipValueDoubleSpinBox.value()
        grid = self.imageAdjustmentClaheGridValueDoubleSpinBox.value()

        threshold = self.imageAdjustmentThresholdPushButton.isChecked()
        threshold_percent = self.imageAdjustmentThresholdSlider.value() / 100
        self.imageAdjustmentThresholdLabel.setText(str(self.imageAdjustmentThresholdSlider.value()))

        image_adjustment_params = {'clahe': clahe, 'clip': clip, 'grid': grid, 'threshold': threshold,
                                   'threshold_percent': threshold_percent}
        self.image_adjustment_params_signal.emit(image_adjustment_params)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def robot_control_slot(self, robot_signal):
        logging.info(robot_signal)
        cx, cy, robot = robot_signal

    def toggle_robot_detection(self):
        state = self.detectRobotsPushButton.isChecked()
        self.enable_robot_detection_signal.emit(state)

    def toggle_cell_detection(self):
        state = self.detectCellsPushButton.isChecked()
        self.enable_cell_detection_signal.emit(state)

    def change_detection_model(self):
        file_name = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                               'Open detection model',
                                                               self.default_directory + '/OET/cnn_models')
        self.detection_model_loc = file_name
        detection.change_model(file_name)


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

    def toggle_dmd_overlay(self):
        state = self.oetToggleDMDAreaOverlayPushButton.isChecked()
        self.image_viewer.toggle_dmd_overlay(state)

    def load_oet_projection(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file for projection', self.default_directory)
        if file_name != '':
            self.load_projection_image(file_name)
            self.oetProjectImagePushButton.setEnabled(True)

    def load_projection_image(self, file_name):
        projection_image = cv2.imread(file_name)
        logging.info(f'loaded image of size {projection_image.shape}')

        # convert to grayscale and binarize
        projection_image = cv2.cvtColor(projection_image, cv2.COLOR_BGR2GRAY)
        ret, projection_image = cv2.threshold(projection_image, 127, 255, cv2.THRESH_BINARY)
        logging.info(f'image converted to binary. shape: {projection_image.shape}')
        self.projection_image = np.copy(projection_image)

    def calibrate_dmd(self):
        logging.info('calibrating dmd...')
        # now we want to project 3 circles on the dmd for the user to click so that we can calibrate
        QtWidgets.QMessageBox.about(self, 'Calibration',
                                    'Please click the center of the upper left and lower right corners of the DMD.')
        self.dmd.project_calibration_image()
        self.image_viewer.calibration_payload = []
        self.image_viewer.calibrating = True

    def update_detection_params(self):
        params_dict = {'buffer_size': int(self.bufferSizeDoubleSpinBox.value()),
                       'dilation_size': int(self.dilationSizeDoubleSpinBox.value()),
                       'objective': self.magnificationComboBoxWidget.currentText()}
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

    def toggleFgOutput(self):
        state = self.fgOutputTogglePushButton.isChecked()
        self.function_generator.change_output(int(state))

    def toggleDrawPaths(self):
        state = self.drawPathsPushButton.isChecked()
        self.image_viewer.drawing_path = state

    def toggleControlDetected(self):
        self.image_viewer.controlling_detected = self.oetControlDetectedPushButton.isChecked()

    def closeEvent(self, event):
        logging.info('closing all connections...')
        for hardware in [self.microscope, self.function_generator,
                         self.dmd, self.pump]:
            if hardware is not False:
                hardware.__del__()
        logging.info('shutdown complete. exiting...')

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
            self.microscope.move_rel_z(self.zstageStepSizeDoubleSpinBox.value() * 40)
            return
        elif key == QtCore.Qt.Key_PageDown:
            self.microscope.move_rel_z(-self.zstageStepSizeDoubleSpinBox.value() * 40)
            return
        if self.project_image_mode:
            self.handle_robot_movement(key)
        if key == QtCore.Qt.Key_Space:
            self.fgOutputTogglePushButton.setChecked(True)

    def keyReleaseEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Space:
            self.fgOutputTogglePushButton.setChecked(False)

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
        f = self.frequencyDoubleSpinBox.value() * 1000
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
        self.scaleBarTogglePushButton.click()
        self.scaleBarTogglePushButton.click()

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

    def toggleScaleBar(self):
        objective = self.magnificationComboBoxWidget.currentText()
        self.toggle_scale_bar_signal.emit(objective)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    window.activateWindow()
    sys.exit(app.exec_())
