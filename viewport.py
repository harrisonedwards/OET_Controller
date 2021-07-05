import os, sys, time
from time import strftime
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import cv2
import enum
from control.micromanager import Camera
from detection import get_robot_control
import matplotlib.pyplot as plt


class CameraType(enum.Enum):
    HAMAMATSU = 1
    NIKON = 2


camera_type = CameraType.NIKON

if camera_type is CameraType.NIKON:
    NATIVE_CAMERA_WIDTH = 2060
    NATIVE_CAMERA_HEIGHT = 2048
if camera_type == 'hamamatsu':
    NATIVE_CAMERA_WIDTH = 2048
    NATIVE_CAMERA_HEIGHT = 2048


class ViewPort(QtCore.QThread):
    # VideoSignal = QtCore.pyqtSignal(QtGui.QImage)
    VideoSignal = QtCore.pyqtSignal('PyQt_PyObject')

    # vid_process_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(ViewPort, self).__init__(parent)
        self.exposure = 200
        self.resize_lock = QtCore.QMutex()
        self.total = 0
        self.width = 0
        self.height = 0
        self.detection = False
        self.robots = {}

        print('initializing camera...')
        if camera_type is CameraType.NIKON:
            self.init_nikon()
        if camera_type is CameraType.HAMAMATSU:
            self.init_hamamatsu()

        self.run_video = True
        self.rotation = False
        self.window_size = QtCore.QSize(self.height, self.width)

        # initialize all of our empty masks
        self.robot_control_mask = np.zeros((NATIVE_CAMERA_HEIGHT, NATIVE_CAMERA_WIDTH), dtype=np.uint8)
        self.path_overlay = np.zeros((NATIVE_CAMERA_HEIGHT, NATIVE_CAMERA_WIDTH, 3), dtype=np.uint8)
        self.detection_overlay = np.zeros((NATIVE_CAMERA_HEIGHT, NATIVE_CAMERA_WIDTH, 3), dtype=np.uint8)

        self.image = np.zeros((NATIVE_CAMERA_HEIGHT, NATIVE_CAMERA_WIDTH))
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
        self.mmc.setCircularBufferMemoryFootprint(1000)
        self.mmc.loadDevice('camera', 'PCO_Camera', 'pco_camera')
        self.mmc.initializeAllDevices()
        self.mmc.setCameraDevice('camera')
        properties = self.mmc.getDevicePropertyNames('camera')
        for p in properties:
            print(p, self.mmc.getProperty('camera', p), self.mmc.getAllowedPropertyValues('camera', p))
        self.mmc.setProperty('camera', 'Exposure', self.exposure)
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

    @QtCore.pyqtSlot()
    def startVideo(self):
        print('starting video stream...')

        count = 0
        QtWidgets.QApplication.processEvents()
        while self.run_video:
            # TODO fix, if possible
            time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
            QtWidgets.QApplication.processEvents()
            if self.mmc.getRemainingImageCount() > 0:
                try:
                    img = self.mmc.getLastImage()
                    img = (img / 256).astype(np.uint8)
                    self.image = img
                except Exception as e:
                    print(f'camera dropped frame {count}, {e}')
                self.process_and_emit_image(img)
            else:
                count += 1
                print('Camera dropped frame:', count)
            QtWidgets.QApplication.processEvents()

    def process_and_emit_image(self, np_img):
        # np_img is native resolution from camera

        if self.detection:
            # if its not in color, convert to color
            if self.detection_overlay.shape[-1] != 3:
                self.detection_overlay = cv2.cvtColor(self.detection_overlay, cv2.COLOR_GRAY2BGR)
                # now make it red only
                self.detection_overlay[:, :, 1:] = 0
            # np_img = (np_img / 256)
            np_img = cv2.cvtColor(np_img, cv2.COLOR_GRAY2BGR)

            np_img = cv2.addWeighted(np_img, 1, self.detection_overlay, 0.5, 0)
            np_img = cv2.addWeighted(np_img, 1, self.path_overlay, 0.5, 0)

        window_h = self.window_size.height()
        window_w = self.window_size.width()

        self.resize_lock.lock()
        # resize and rotate
        if self.rotation:
            np_img = cv2.rotate(np_img, cv2.cv2.ROTATE_90_COUNTERCLOCKWISE)
        np_img = cv2.resize(np_img, (window_h, window_w))
        self.resize_lock.unlock()

        # emit our array, whatever shape it may be
        if self.run_video:
            self.VideoSignal.emit(np_img)

        # if self.detection:
        #     self.qt_image = QtGui.QImage(np_img.data, window_w, window_h,
        #                                  np_img.strides[0], QtGui.QImage.Format_RGB16)
        # else:
        #     self.qt_image = QtGui.QImage(np_img.data, window_w, window_h, np_img.strides[0],
        #                                  QtGui.QImage.Format_Grayscale16)

    @QtCore.pyqtSlot()
    def run_detection_slot(self):
        print('running detection...')
        self.clear_overlay_slot()
        self.detection = True
        self.robot_control_mask, robot_contours, robot_angles = get_robot_control(self.image)
        self.detection_overlay = np.copy(self.robot_control_mask)
        for i in range(len(robot_contours)):
            name = f'robot_{i}'
            self.robots[name] = {'contour': robot_contours[i], 'angle': robot_angles[i]}
        print(f'found {len(robot_contours)} robots')

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
    def path_slot(self, payload):
        if len(self.robots.items()) == 0:
            print('no robots currently detected for paths..')
            return

        # find nearest robot here and add it to the dictionary
        cx, cy, nearest_robot = self.find_closest_robot(payload)

        # unit normalize all
        self.robots[nearest_robot]['path_start_x'] = cx / self.width
        self.robots[nearest_robot]['path_start_y'] = cy / self.height
        self.robots[nearest_robot]['path_end_x'] = payload['end_x'] / self.width
        self.robots[nearest_robot]['path_end_y'] = payload['end_y'] / self.height
        print('nearest robot:', nearest_robot)
        # print('robots:', self.robots)
        self.draw_paths()

    def draw_paths(self):
        self.path_overlay = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # find closest contour, color the robot the same as the path, and draw it
        for robot in self.robots:
            if 'path_start_x' in self.robots[robot].keys():
                start_x_scaled = int(self.robots[robot]['path_start_x'] * self.width)
                start_y_scaled = int(self.robots[robot]['path_start_y'] * self.height)
                end_x_scaled = int(self.robots[robot]['path_end_x'] * self.width)
                end_y_scaled = int(self.robots[robot]['path_end_y'] * self.height)
                cv2.line(self.path_overlay, (start_x_scaled, start_y_scaled),
                         (end_x_scaled, end_y_scaled), (0, 255, 0), 2)
        self.path_overlay = cv2.resize(self.path_overlay, (self.width, self.height), dtype=np.uint8)

    @QtCore.pyqtSlot()
    def clear_overlay_slot(self):
        self.robots = {}
        self.path_overlay[:, :, :] = 0
        self.detection_overlay[:, :, :] = 0
        self.detection = False

    @QtCore.pyqtSlot(QtCore.QSize, 'PyQt_PyObject')
    def resize_slot(self, size, running):
        print('received resize')
        self.resize_lock.lock()
        # print('resize locked')
        self.width = size.width()
        self.height = size.height()
        self.image = np.zeros((self.height, self.width), dtype=np.uint8)

        self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
                                     self.window_size.width(), QtGui.QImage.Format_Grayscale8)
        # self.VideoSignal.emit(self.qt_image)
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

    # @QtCore.pyqtSlot(QtCore.QSize, 'PyQt_PyObject')
    # def resize_slot(self, size, running):
    #     # print('received resize')
    #     self.image = np.zeros((2060, 2048))
    #     self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
    #                                  self.window_size.width(), QtGui.QImage.Format_Grayscale16)
    #     self.VideoSignal.emit(self.qt_image)
    #     if running:
    #         self.run_video = False
    #         time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
    #     else:
    #         self.window_size = size
    #         self.run_video = True
    #         self.startVideo()

    # # print('received resize')
    # self.image = np.zeros((2060, 2048))
    # self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
    #                              self.window_size.width(), QtGui.QImage.Format_Grayscale16)
    # self.VideoSignal.emit(self.qt_image)
    # if running:
    #     self.run_video = False
    #     time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
    # else:
    #     self.window_size = size
    #     self.run_video = True
    #     self.startVideo()

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
