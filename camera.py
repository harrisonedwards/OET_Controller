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
import qimage2ndarray

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
        self.waiting = False

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
        self.image = np.zeros((width, height, 3)).astype(np.uint8)
        self.overlay = np.zeros((width, height, 3)).astype(np.uint8)
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
            np_img = np.frombuffer(self.cam_buffer, dtype=np.uint8).reshape((1024, 1536, 3))

            # for screenshots:
            self.image = np.copy(np_img)

            np_img = cv2.resize(np_img, (self.width, self.height)).astype(np.uint8)

            np_img = cv2.addWeighted(np_img, 1, self.overlay, 0.5, 0)

            self.VideoSignal.emit(np_img)
        else:
            print('event callback: {}'.format(nEvent))


    @QtCore.pyqtSlot('PyQt_PyObject')
    def path_slot(self, payload):
        # unit normalize all paths
        payload['start_x'] /= self.width
        payload['start_y'] /= self.height
        payload['end_x'] /= self.width
        payload['end_y'] /= self.height
        self.paths.append(payload)
        self.draw_paths()

    def draw_paths(self):
        self.overlay = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        if len(self.paths) > 0:
            for path in self.paths:
                start_x_scaled = int(path['start_x'] * self.width)
                start_y_scaled = int(path['start_y'] * self.height)
                end_x_scaled = int(path['end_x'] * self.width)
                end_y_scaled = int(path['end_y'] * self.height)
                cv2.line(self.overlay, (start_x_scaled, start_y_scaled),
                         (end_x_scaled, end_y_scaled), (0, 255, 0), 2)
        self.overlay = cv2.resize(self.overlay, (self.width, self.height)).astype(np.uint8)

    @QtCore.pyqtSlot()
    def clear_paths_slot(self):
        self.paths = []
        self.draw_paths()

    @QtCore.pyqtSlot(QtCore.QSize, 'PyQt_PyObject')
    def resize_slot(self, size, running):
        print('received resize')
        self.width = size.width()
        self.height = size.height()
        self.image = np.zeros((self.height, self.width, 3)).astype(np.uint8)
        self.overlay = np.zeros((self.height, self.width, 3)).astype(np.uint8)
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
