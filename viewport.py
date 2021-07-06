import os, sys, time
from time import strftime
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import toupcam
from control.micromanager import Camera
import matplotlib.pyplot as plt
import cv2
import time
from detection import get_robot_control
from object_detection.microrobots import detect_microrobots, draw_microrobots
import enum

class CameraType(enum.Enum):
    HAMAMATSU = 1
    TOUPCAM = 2

camera_type = CameraType.HAMAMATSU

if camera_type is CameraType.TOUPCAM:
    NATIVE_CAMERA_WIDTH = 2048
    NATIVE_CAMERA_HEIGHT = 2060
if camera_type is CameraType.HAMAMATSU:
    NATIVE_CAMERA_WIDTH = 2048
    NATIVE_CAMERA_HEIGHT = 2048

class ViewPort(QtCore.QThread):
    VideoSignal = QtCore.pyqtSignal('PyQt_PyObject')

    # vid_process_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(ViewPort, self).__init__(parent)
        self.exposure = 200
        self.resize_lock = QtCore.QMutex()
        self.detection_lock = QtCore.QMutex()
        self.hcam = None
        self.cam_buffer = None
        self.img_buffer = None
        self.total = 0
        self.width = 0
        self.height = 0
        self.detection = False
        self.robots = {}



        self.run_video = True
        self.rotation = False
        self.window_size = QtCore.QSize(self.width, self.height)  # original image size
        self.image = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        self.robot_control_mask = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        self.path_overlay = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        self.detection_overlay = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        print('initializing camera...')
        if camera_type is CameraType.TOUPCAM:
            self.init_toupcam()
        if camera_type is CameraType.HAMAMATSU:
            self.init_hamamatsu()
        self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
                                     self.window_size.width(), QtGui.QImage.Format_RGB888)

    def init_hamamatsu(self):
        self.hcam = Camera(parent=self)
        self.width = self.hcam.width
        self.height = self.hcam.height
        self.hcam.start_sequence_qt(self.VideoSignal.emit)

    def init_toupcam(self):
        a = toupcam.Toupcam.EnumV2()
        self.hcam = toupcam.Toupcam.Open(a[0].id)
        if self.hcam:
            width, height = self.hcam.get_Size()

            # set for quarter res for quicker acquisition
            width = width // 2
            height = height // 2
            self.hcam.put_Size(int(width), int(height))

            self.width = width
            self.height = height
            buffsize = ((width * 24 + 31) // 32 * 4) * height
            print('image size: {} x {}, buffsize = {}'.format(width, height, buffsize))
            self.cam_buffer = bytes(buffsize)
            print('starting video stream...')
            if self.cam_buffer:
                self.hcam.put_Option(toupcam.TOUPCAM_OPTION_BYTEORDER, 0)
                self.hcam.put_Option(toupcam.TOUPCAM_OPTION_BITDEPTH, 0)

                self.hcam.put_ExpoTime(15000)
                self.hcam.StartPullModeWithCallback(self.cameraCallback, self)

    def __del__(self):
        self.hcam.Close()
        self.hcam = None
        self.cam_buffer = None


    # the vast majority of callbacks come from toupcam.dll/so/dylib internal threads
    @staticmethod
    def cameraCallback(nEvent, ctx):
        if nEvent == toupcam.TOUPCAM_EVENT_IMAGE:
            ctx.CameraCallback(nEvent)

    def CameraCallback(self, nEvent):
        if nEvent == toupcam.TOUPCAM_EVENT_IMAGE and self.run_video:
            self.hcam.PullImageV2(self.cam_buffer, 24, None)

            # raw image:
            # np_img = np.frombuffer(self.cam_buffer, dtype=np.uint8).reshape((1024, 1536, 3))

            # HALLUCINATION IMAGE:
            np_img = cv2.imread(r'C:\Users\Wheeler Lab\Desktop\Harrison\OET\2021_05_12_17_39_14.png')
            self.process_and_emit_image(np_img)
        else:
            print('event callback: {}'.format(nEvent))

    def process_and_emit_image(self,np_img):

        # for screenshots:
        self.image = np.copy(np_img)

        if self.detection and self.detection_lock.tryLock(10):
            if self.detection_overlay.shape[-1] != 3:
                self.detection_overlay = cv2.cvtColor(self.detection_overlay, cv2.COLOR_GRAY2BGR)
                # make it red only
                self.detection_overlay[:, :, 1:] = 0

            np_img = cv2.addWeighted(np_img, 1, self.detection_overlay, 0.5, 0)
            self.detection_lock.unlock()
        #print('image locking')
        self.resize_lock.lock()
        #print('image locked')
        np_img = cv2.resize(np_img, (self.width, self.height)).astype(np.uint8)

        np_img = cv2.addWeighted(np_img, 1, self.path_overlay, 0.5, 0)
        #print('image unlocking')
        self.resize_lock.unlock()
        self.VideoSignal.emit(np_img)


    @QtCore.pyqtSlot()
    def run_detection_slot(self):
        print('running detection...')
        if self.detection_lock.tryLock(10):
            self.clear_overlay_slot()
            self.detection = True
            #self.robot_control_mask, robot_contours, robot_angles = get_robot_control(self.image,100,200)
            robots, _ = detect_microrobots(self.image,'intensity')

            self.detection_overlay = np.ones((self.image.shape[0],self.image.shape[1]),dtype=self.image.dtype)
            self.detection_overlay = draw_microrobots(self.detection_overlay,robots,as_mask=False,draw_value=255,thickness=5)

            for i in range(len(robots)):
                name = f'robot_{i}'
                self.robots[name] = {'centre': robots[i,:2], 'radius':robots[i,2], 'angle': robots[i,3]}
            print(f'found {len(robots)} robots')
            self.detection_lock.unlock()

    def find_closest_robot(self, payload):
        min_d = np.inf
        nearest_robot = None
        nearest_robot_cx = None
        nearest_robot_cy = None
        for robot in self.robots:
            # contour = self.robots[robot]['contour']
            # M = cv2.moments(contour)
            #
            # # unit normalize our native image width and the window width for comparison
            # cx = int(M["m10"] / M["m00"]) / NATIVE_CAMERA_WIDTH
            # cy = int(M["m01"] / M["m00"]) / NATIVE_CAMERA_HEIGHT
            cx,cy = self.robots[robot]['centre']/[NATIVE_CAMERA_WIDTH,NATIVE_CAMERA_HEIGHT]
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
        self.path_overlay = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        # find closest contour, color the robot the same as the path, and draw it
        for robot in self.robots:
            if 'path_start_x' in self.robots[robot].keys():
                start_x_scaled = int(self.robots[robot]['path_start_x'] * self.width)
                start_y_scaled = int(self.robots[robot]['path_start_y'] * self.height)
                end_x_scaled = int(self.robots[robot]['path_end_x'] * self.width)
                end_y_scaled = int(self.robots[robot]['path_end_y'] * self.height)
                cv2.line(self.path_overlay, (start_x_scaled, start_y_scaled),
                         (end_x_scaled, end_y_scaled), (0, 255, 0), 2)
        self.path_overlay = cv2.resize(self.path_overlay, (self.width, self.height)).astype(np.uint8)

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
        #print('resize locked')
        self.width = size.width()
        self.height = size.height()
        self.image = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        self.path_overlay = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        # self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
        #                              self.window_size.width(), QtGui.QImage.Format_Grayscale8)
        # self.VideoSignal.emit(self.qt_image)
        if running:
            self.run_video = False
            time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
        else:
            self.window_size = size
            self.run_video = True
        if len(self.robots.items()) > 0:
            self.draw_paths()
        #print('resize unlocking')
        self.resize_lock.unlock()

    @QtCore.pyqtSlot('PyQt_PyObject')
    def set_exposure_slot(self, exposure):
        print(f'set exposure: {exposure}')
        if camera_type is CameraType.TOUPCAM:
            self.hcam.put_ExpoTime(int(exposure * 10))
        if camera_type is CameraType.HAMAMATSU:
            self.hcam.set_exposure(exposure)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def set_gain_slot(self, gain):
        gain = int(gain * 100)
        print(f'set gain: {gain}')
        if camera_type is CameraType.TOUPCAM:
            self.hcam.put_ExpoAGain(gain)


    @QtCore.pyqtSlot()
    def take_screenshot_slot(self):
        cv2.imwrite(
            'C:\\Users\\Mohamed\\Desktop\\Harrison\\Screenshots\\' + strftime('%Y_%m_%d_%H_%M_%S.png', time.gmtime()),
            self.image)

# if __name__ == '__main__':
#     cam = Cam()
#     img = cam.get_image()
#     plt.imshow(img)
#     plt.show()
