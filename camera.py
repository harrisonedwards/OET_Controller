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

class Camera(QtCore.QThread):
    VideoSignal = QtCore.pyqtSignal(QtGui.QImage)

    # vid_process_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(Camera, self).__init__(parent)
        self.exposure = 200
        self.count = 0

        self.hcam = None
        self.cam_buffer = None
        self.img_buffer = None
        self.total = 0
        self.width = 0
        self.height = 0
        self.waiting = False

        print('initializing camera...')
        a = toupcam.Toupcam.EnumV2()
        self.hcam = toupcam.Toupcam.Open(a[0].id)
        if self.hcam:
            width, height = self.hcam.get_Size()

            # set for quarter res for quicker acquisition
            width = width // 2
            height = height //2
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
        self.window_size = QtCore.QSize(width, height) # original image size
        self.image = np.zeros((width, height))
        self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
                                     self.window_size.width(), QtGui.QImage.Format_Grayscale8)

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
            img = QtGui.QImage(self.cam_buffer, self.width, self.height, (self.width * 24 + 31) // 32 * 4,
                               QtGui.QImage.Format_RGB888)
            self.VideoSignal.emit(img)
            self.count += 1
            print(self.count)
        else:
            print('event callback: {}'.format(nEvent))


    @QtCore.pyqtSlot()
    def startVideo(self):
        count = 0
        # QtWidgets.QApplication.processEvents()
        # while self.run_video:
        #     try:
        #         img = self.nextImage()
        #
        #         window_h = self.window_size.height()
        #         window_w = self.window_size.width()
        #
        #         # if self.rotation:
        #         #     img = cv2.rotate(img, cv2.cv2.ROTATE_90_COUNTERCLOCKWISE)
        #
        #         # for screenshots:
        #         self.image = np.copy(img)
        #
        #         img = cv2.resize(img, (window_h, window_w))
        #         self.qt_image = QtGui.QImage(img.data, window_w, window_h,
        #                                      img.strides[0], QtGui.QImage.Format_Grayscale8)
        #         count += 1
        #         if count % 10 == 0:
        #             print(f'at frame {count}')
        #         self.VideoSignal.emit(self.qt_image)
        #     except Exception as e:
        #         print(f'camera dropped frame {count}, {e}')
        #     QtWidgets.QApplication.processEvents()

    @QtCore.pyqtSlot(QtCore.QSize, 'PyQt_PyObject')
    def resize_slot(self, size, running):
        # print('received resize')
        self.image = np.zeros((self.width, self.height))
        self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
                                     self.window_size.width(), QtGui.QImage.Format_Grayscale8)
        self.VideoSignal.emit(self.qt_image)
        if running:
            self.run_video = False
            time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
        else:
            self.window_size = size
            self.run_video = True
            self.startVideo()

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