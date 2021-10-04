import os, sys, time
from time import strftime

import names
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import cv2
import enum
from control.micromanager import Camera
from detection import get_robot_control
import imageio
import matplotlib.pyplot as plt


class CameraType(enum.Enum):
    HAMAMATSU = 1
    NIKON = 2


camera_type = CameraType.NIKON

if camera_type is CameraType.NIKON:
    NATIVE_CAMERA_WIDTH = 2048
    NATIVE_CAMERA_HEIGHT = 2060
if camera_type == 'hamamatsu':
    NATIVE_CAMERA_WIDTH = 2048
    NATIVE_CAMERA_HEIGHT = 2048


class imageProcessor(QtCore.QThread):
    # VideoSignal = QtCore.pyqtSignal(QtGui.QImage)
    VideoSignal = QtCore.pyqtSignal('PyQt_PyObject')
    robot_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(imageProcessor, self).__init__(parent)
        self.exposure = 200
        self.resize_lock = QtCore.QMutex()
        self.total = 0
        self.width = 0
        self.height = 0
        self.detection = False
        self.robots = {}
        self.recording = False
        self.writer = None
        self.video_dir = 'C:\\Users\\Mohamed\\Desktop\\Harrison\\Videos\\'
        self.vid_name = ''
        self.clahe_params = {'status': False}

        print('initializing camera...')
        if camera_type is CameraType.NIKON:
            self.init_nikon()
        if camera_type is CameraType.HAMAMATSU:
            self.init_hamamatsu()

        self.run_video = True
        self.window_size = QtCore.QSize(self.height, self.width)
        self.buffer_size = 10
        self.dilation_size = 30
        self.open_robots = False

        # initialize all of our empty masks
        self.path_overlay = np.zeros((NATIVE_CAMERA_WIDTH, NATIVE_CAMERA_HEIGHT, 3), dtype=np.uint8)
        self.detection_overlay = np.zeros((NATIVE_CAMERA_WIDTH, NATIVE_CAMERA_HEIGHT, 3), dtype=np.uint8)

        self.image = np.zeros((NATIVE_CAMERA_WIDTH, NATIVE_CAMERA_HEIGHT))
        self.window_size = QtCore.QSize(self.height, self.width)  # original image size
        self.qt_image = QtGui.QImage(self.image.data, self.height,
                                     self.width, QtGui.QImage.Format_Grayscale8)

    def init_nikon(self):
        # start micromanager and grab camera
        mm_directory = 'C:\\Program Files\\Micro-Manager-2.0gamma'
        sys.path.append(mm_directory)
        os.chdir(mm_directory)

        import MMCorePy
        self.mmc = MMCorePy.CMMCore()
        self.mmc.setCircularBufferMemoryFootprint(500)
        self.mmc.loadDevice('camera', 'PCO_Camera', 'pco_camera')
        self.mmc.initializeAllDevices()
        self.mmc.setCameraDevice('camera')
        properties = self.mmc.getDevicePropertyNames('camera')
        self.mmc.setProperty('camera', 'PixelRate', 'fast scan')
        self.mmc.setProperty('camera', 'Noisefilter', 'Off')
        self.mmc.setProperty('camera', 'Exposure', self.exposure)
        # self.mmc.setProperty('camera', 'PixelType', '8bit')
        for p in properties:
            print(p, self.mmc.getProperty('camera', p), self.mmc.getAllowedPropertyValues('camera', p))
        self.mmc.startContinuousSequenceAcquisition(1)
        self.run_video = True

    def init_hamamatsu(self):
        self.hcam = Camera()
        self.width = Camera.width
        self.height = Camera.height
        self.hcam.start_sequence_qt(self.process_and_emit_image)

    def __del__(self):
        print('closing camera...')
        self.mmc.stopSequenceAcquisition()
        self.mmc.reset()

    @QtCore.pyqtSlot('PyQt_PyObject')
    def update_detection_params_slot(self, params_dict):
        self.buffer_size = params_dict['buffer_size']
        self.dilation_size = params_dict['dilation_size']
        self.objective = params_dict['objective']
        self.open_robots = params_dict['open_robots']
        print('detection params updated:', params_dict)

    @QtCore.pyqtSlot()
    def startVideo(self):
        print('starting video stream...')
        count = 0
        t0 = time.time()
        QtWidgets.QApplication.processEvents()
        while self.run_video:
            # TODO fix, if possible
            # time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
            QtWidgets.QApplication.processEvents()
            if self.mmc.getRemainingImageCount() > 0:
                try:
                    img = self.mmc.getLastImage()
                    # img = np.right_shift(img, 1)
                    img = (img / 256).astype(np.uint8)
                    if self.recording:
                        self.writer.append_data(img)
                    self.image = img
                except Exception as e:
                    print(f'camera dropped frame {count}, {e}')
                # self.VideoSignal.emit(img)
                self.process_and_emit_image(img)
                count += 1
                if count % 5 == 0 and self.detection:
                    self.run_detection()
                if count % 200 == 0:
                    t1 = time.time()
                    fps = 200 / (t1 - t0)
                    t0 = t1
                    print(f'fps: {fps}')
            else:
                count += 1
                print('Camera dropped frame:', count)
            QtWidgets.QApplication.processEvents()

    def process_and_emit_image(self, np_img):
        # np_img is native resolution from camera

        if self.clahe_params['status']:
            clahe = cv2.createCLAHE(clipLimit=self.clahe_params['clip'],
                                    tileGridSize=(self.clahe_params['grid'], self.clahe_params['grid']))
            np_img = clahe.apply(np_img)

        if self.detection:
            np_img = cv2.cvtColor(np_img, cv2.COLOR_GRAY2BGR)
            np_img = cv2.addWeighted(np_img, 1, self.detection_overlay, 0.8, 0)
            np_img = cv2.addWeighted(np_img, 1, self.path_overlay, 0.8, 0)

        window_h = self.window_size.height()
        window_w = self.window_size.width()

        # resize
        self.resize_lock.lock()
        np_img = cv2.resize(np_img, (window_w, window_h))
        self.resize_lock.unlock()

        # emit our array, whatever shape it may be
        if self.run_video:
            self.VideoSignal.emit(np_img)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def toggle_detection_slot(self, state):
        self.detection = state
        if not self.detection:
            self.clear_paths_overlay_slot()
            self.robots = {}

    def get_control_mask(self, robots):
        objective_calibration_dict = {'2x': [8, 0.25],
                                      '4x': [4, 0.5],
                                      '10x': [2, 1],
                                      '20x': [1, 2],
                                      '40x': [0.5, 4]}

        robot_control_mask = np.zeros(self.image.shape + (3,), dtype=np.uint8)

        line_length = int(200 * objective_calibration_dict[self.objective][1])
        line_width = int(80 * objective_calibration_dict[self.objective][1])
        robot_center_radius = 120 // objective_calibration_dict[self.objective][0]

        for robot in robots:
            contour = robots[robot]['contour']
            angle = robots[robot]['angle']

            M = cv2.moments(contour)
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            # draw the contours on our control mask
            if 'control' in robots[robot].keys():
                if robots[robot]['control']:
                    # green for the controlled robot
                    robot_control_mask = cv2.drawContours(robot_control_mask, [contour], -1, (0, 255, 0), -1)
                    cv2.circle(robot_control_mask, (cx, cy), robot_center_radius, (0, 255, 0), -1)
            else:
                # red for all non-controlled, but detected robots
                robot_control_mask = cv2.drawContours(robot_control_mask, [contour], -1, (255, 0, 0), -1)
                cv2.circle(robot_control_mask, (cx, cy), robot_center_radius, (255, 0, 0), -1)

            if self.open_robots:
                # draw a blank line to remove the opening for the robot
                try:
                    cv2.line(robot_control_mask, (cx, cy),
                             (cx + int(line_length * np.cos(angle)), cy + int(line_length * np.sin(angle))), (0, 0, 0),
                             line_width)
                except Exception as e:
                    print('failed to draw line to open robots')

        robot_control_mask = cv2.dilate(robot_control_mask, np.ones((self.buffer_size, self.buffer_size)))

        dilation = np.copy(robot_control_mask)
        dilation = cv2.dilate(dilation, np.ones((self.dilation_size, self.dilation_size)) * 255).astype(np.uint8)

        robot_control_mask = dilation - robot_control_mask

        return robot_control_mask

    def run_detection(self):
        # process current image to find robots
        robot_contours, robot_angles = get_robot_control(self.image, self.objective)

        if len(robot_contours) == 0:
            # no robots found
            self.detection_overlay.fill(0)
            return

        if self.robots == {}:
            print('initial finding of robots...')
            # first time finding robots, so lets update our finding them
            for i in range(len(robot_contours)):
                name = names.get_first_name()
                self.robots[name] = {'contour': robot_contours[i], 'angle': robot_angles[i]}
        else:
            # update our understanding of the robots
            self.update_robot_information(robot_contours, robot_angles)

        self.detection_overlay = self.get_control_mask(self.robots).astype(np.uint8)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def robot_control_slot(self, payload):
        if len(self.robots.items()) == 0:
            print('no robots currently detected for control...ignoring.')
            return
        # find nearest robot here and add it to the dictionary
        cx, cy, nearest_robot = self.find_closest_robot(payload)
        self.robots[nearest_robot]['control'] = True
        print(f'found closest robot at {cx}, {cy}')
        self.robot_signal.emit((cx, cy, nearest_robot))

    def update_robot_information(self, new_robot_contours, new_robot_angles):
        # we want to see if our newly detected robots are similar to our old robots, given a distance threshold
        similarity_threshold = .3
        for robot in self.robots:
            old_contour = self.robots[robot]['contour']
            for new_contour, new_angle in zip(new_robot_contours, new_robot_angles):
                if cv2.matchShapes(new_contour, old_contour, 2, 0) < similarity_threshold:
                    # they are a match! let's update the robot internal dictionary
                    self.robots[robot]['contour'] = new_contour
                    self.robots[robot]['angle'] = new_angle
                    print(f'robot {robot} found and kept consistent. {len(new_robot_contours)} total robots')
                else:
                    # we need to add the new robot to our dictionary
                    name = names.get_first_name()
                    while name in self.robots.keys():
                        name = names.get_first_name()
                    self.robots[robot] = {'contour': new_contour, 'angle': new_angle}
                    # print(f'new robot {name} found and added to tracking...')

    def find_closest_robot(self, payload):
        min_d = np.inf
        nearest_robot = None
        nearest_robot_cx = None
        nearest_robot_cy = None
        for robot in self.robots:
            contour = self.robots[robot]['contour']
            M = cv2.moments(contour)

            # unit normalize our native image width and the window width for comparison
            cx = int(M["m10"] / M["m00"]) / NATIVE_CAMERA_WIDTH
            cy = int(M["m01"] / M["m00"]) / NATIVE_CAMERA_HEIGHT
            click_x = payload['start_x'] / self.width
            click_y = payload['start_y'] / self.height

            # find minimum
            d = np.sqrt((cx - click_x) ** 2 + (cy - click_y) ** 2)
            if d < min_d:
                min_d = d
                nearest_robot = robot
                nearest_robot_cx = cx
                nearest_robot_cy = cy

        # scale back to window size
        return nearest_robot_cx * self.width, nearest_robot_cy * self.height, nearest_robot

    @QtCore.pyqtSlot('PyQt_PyObject')
    def clay_params_slot(self, clahe_params):
        self.clahe_params = clahe_params

    @QtCore.pyqtSlot('PyQt_PyObject')
    def path_slot(self, payload):
        if len(self.robots.items()) == 0:
            print('no robots currently detected for paths..')
            return

        # find nearest robot here and add it to the dictionary
        cx, cy, nearest_robot = self.find_closest_robot(payload)

        # unit normalize all
        # need to add x-offsets for the black part of the scaled image...
        self.robots[nearest_robot]['path_start_x'] = cx / self.width
        self.robots[nearest_robot]['path_start_y'] = cy / self.height
        self.robots[nearest_robot]['path_end_x'] = payload['end_x'] / self.width
        self.robots[nearest_robot]['path_end_y'] = payload['end_y'] / self.height
        print('nearest robot:', nearest_robot)
        # print('robots:', self.robots)
        self.draw_paths()

    def draw_paths(self):
        self.path_overlay = np.zeros((NATIVE_CAMERA_WIDTH, NATIVE_CAMERA_HEIGHT, 3), dtype=np.uint8)
        # find closest contour, color the robot the same as the path, and draw it
        for robot in self.robots:
            if 'path_start_x' in self.robots[robot].keys():
                start_x_scaled = int(self.robots[robot]['path_start_x'] * NATIVE_CAMERA_WIDTH)
                start_y_scaled = int(self.robots[robot]['path_start_y'] * NATIVE_CAMERA_HEIGHT)
                end_x_scaled = int(self.robots[robot]['path_end_x'] * NATIVE_CAMERA_WIDTH)
                end_y_scaled = int(self.robots[robot]['path_end_y'] * NATIVE_CAMERA_HEIGHT)
                cv2.line(self.path_overlay, (start_x_scaled, start_y_scaled),
                         (end_x_scaled, end_y_scaled), (0, 255, 0), 2)

    @QtCore.pyqtSlot()
    def clear_paths_overlay_slot(self):
        self.path_overlay = np.zeros((NATIVE_CAMERA_WIDTH, NATIVE_CAMERA_HEIGHT, 3), dtype=np.uint8)

    @QtCore.pyqtSlot(QtCore.QSize, 'PyQt_PyObject')
    def resize_slot(self, size, running):
        # print('received resize')

        # self.detection = False
        self.clear_paths_overlay_slot()

        self.resize_lock.lock()
        self.width = size.width()
        self.height = size.height()
        self.image = np.zeros((self.height, self.width), dtype=np.uint8)
        self.VideoSignal.emit(self.image)

        if running:
            self.run_video = False
            time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
        else:
            self.window_size = size
            self.run_video = True
        if len(self.robots.items()) > 0:
            self.draw_paths()
        self.resize_lock.unlock()

    @QtCore.pyqtSlot('PyQt_PyObject')
    def set_exposure_slot(self, exposure):
        self.exposure = exposure
        self.mmc.setProperty('camera', 'Exposure', self.exposure)
        print('exposure set:', self.exposure)

    @QtCore.pyqtSlot()
    def take_screenshot_slot(self):
        cv2.imwrite(
            'C:\\Users\\Mohamed\\Desktop\\Harrison\\Screenshots\\' + strftime('%Y_%m_%d_%H_%M_%S.png', time.gmtime()),
            self.image)

    @QtCore.pyqtSlot()
    def start_recording_video_slot(self):
        self.recording = True
        self.vid_name = self.video_dir + strftime('%Y_%m_%d_%H_%M_%S.avi', time.gmtime())
        print(f'recording video: {self.vid_name}')
        self.writer = imageio.get_writer(self.vid_name, mode='I')

    @QtCore.pyqtSlot()
    def stop_video_slot(self):
        self.recording = False
        self.writer.close()
        print(f'video: {self.vid_name} finished recording')
