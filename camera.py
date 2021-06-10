import os, sys, time
from time import strftime
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import cv2
import toupcam
import numpy as np
import matplotlib.pyplot as plt
import cv2
import time
from detection import full_process

NATIVE_CAMERA_WIDTH = 2048
NATIVE_CAMERA_HEIGHT = 2060

class Camera(QtCore.QThread):
    VideoSignal = QtCore.pyqtSignal('PyQt_PyObject')

    # vid_process_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(Camera, self).__init__(parent)
        self.exposure = 200

        self.hcam = None
        self.cam_buffer = None
        self.img_buffer = None
        self.total = 0
        self.width = 0
        self.height = 0
        self.detection = False

        self.contours_towards_center = []

        self.paths = []

        print('initializing camera...')
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

        self.run_video = True
        self.rotation = False
        self.window_size = QtCore.QSize(width, height)  # original image size
        self.image = np.zeros((height, width, 3)).astype(np.uint8)
        self.robot_control_mask = np.zeros((height, width, 3)).astype(np.uint8)
        self.path_overlay = np.zeros((height, width, 3)).astype(np.uint8)
        self.detection_overlay = np.zeros((height, width, 3)).astype(np.uint8)
        self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
                                     self.window_size.width(), QtGui.QImage.Format_RGB888)

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

            # for screenshots:
            self.image = np.copy(np_img)

            if self.detection:
                if self.detection_overlay.shape[-1] != 3:
                    self.detection_overlay = cv2.cvtColor(self.detection_overlay, cv2.COLOR_GRAY2BGR)
                    # make it red only
                    self.detection_overlay[:, :, 1:] = 0

                np_img = cv2.addWeighted(np_img, 1, self.detection_overlay, 0.5, 0)

            np_img = cv2.resize(np_img, (self.width, self.height)).astype(np.uint8)

            np_img = cv2.addWeighted(np_img, 1, self.path_overlay, 0.5, 0)


            self.VideoSignal.emit(np_img)
        else:
            print('event callback: {}'.format(nEvent))

    @QtCore.pyqtSlot()
    def run_detection_slot(self):
        print('running detection')
        self.detection = True
        self.robot_control_mask, self.contours_towards_center, robot_angles = full_process(self.image)
        self.detection_overlay = np.copy(self.robot_control_mask)


    def draw_paths(self):
        self.path_overlay = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        # find closest contour, color the robot the same as the path, and draw it
        if len(self.paths) > 0:
            for path in self.paths:
                # start_x_scaled = int(path['start_x'] * self.width)
                # start_y_scaled = int(path['start_y'] * self.height)

                start_x_scaled = int(path['nearest_robot_cx'] * self.width)
                start_y_scaled = int(path['nearest_robot_cy'] * self.height)

                end_x_scaled = int(path['end_x'] * self.width)
                end_y_scaled = int(path['end_y'] * self.height)
                print('line:', (start_x_scaled, start_y_scaled), (end_x_scaled, end_y_scaled))
                cv2.line(self.path_overlay, (start_x_scaled, start_y_scaled),
                         (end_x_scaled, end_y_scaled), (0, 255, 0), 2)
        self.path_overlay = cv2.resize(self.path_overlay, (self.width, self.height)).astype(np.uint8)

    def find_closest_robot(self, payload):
        if len(self.contours_towards_center) == 0:
            print('no robots detected for path')
            return
        min_d = np.inf
        nearest_robot = None
        nearest_robot_cx = None
        nearest_robot_cy = None
        for contour in self.contours_towards_center:
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
                nearest_robot = contour
                nearest_robot_cx = cx
                nearest_robot_cy = cy

        # scale back to window size
        return nearest_robot_cx * self.width, nearest_robot_cy * self.height, nearest_robot

    @QtCore.pyqtSlot('PyQt_PyObject')
    def path_slot(self, payload):
        # find nearest robot here and add it to the dictionary
        cx, cy, nearest_robot = self.find_closest_robot(payload)

        # unit normalize all paths
        payload['end_x'] /= self.width
        payload['end_y'] /= self.height
        payload['nearest_robot'] = nearest_robot
        payload['nearest_robot_cx'] = cx / self.width
        payload['nearest_robot_cy'] = cy / self.height
        self.paths.append(payload)
        self.draw_paths()

    @QtCore.pyqtSlot()
    def clear_overlay_slot(self):
        self.paths = []
        self.draw_paths()
        self.detection = False

    @QtCore.pyqtSlot(QtCore.QSize, 'PyQt_PyObject')
    def resize_slot(self, size, running):
        print('received resize')
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
        self.draw_paths()

    @QtCore.pyqtSlot('PyQt_PyObject')
    def set_exposure_slot(self, exposure):
        print(f'set exposure: {exposure}')
        self.hcam.put_ExpoTime(int(exposure * 10))

    @QtCore.pyqtSlot('PyQt_PyObject')
    def set_gain_slot(self, gain):
        gain = int(gain * 100)
        print(f'set gain: {gain}')
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
