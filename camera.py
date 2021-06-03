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

class Cam:
    def __init__(self):
        self.hcam = None
        self.cam_buffer = None
        self.img_buffer = None
        self.total = 0
        self.width = 0
        self.height = 0
        self.waiting = False

        a = toupcam.Toupcam.EnumV2()
        self.hcam = toupcam.Toupcam.Open(a[0].id)
        if self.hcam:
            width, height = self.hcam.get_Size()
            self.width = width
            self.height = height
            bufsize = ((width * 24 + 31) // 32 * 4) * height
            print('image size: {} x {}, bufsize = {}'.format(width, height, bufsize))
            self.cam_buffer = bytes(bufsize)
            if self.cam_buffer:
                self.hcam.put_Option(toupcam.TOUPCAM_OPTION_BYTEORDER, 1)
                self.hcam.put_ExpoTime(200000)
                self.hcam.StartPullModeWithCallback(self.cameraCallback, self)


    def get_image(self):
        return self.nextImage()

    def __del__(self):
        self.hcam.Close()
        self.hcam = None
        self.cam_buffer = None

    # the vast majority of callbacks come from toupcam.dll/so/dylib internal threads
    @staticmethod
    def cameraCallback(nEvent, ctx):
        if nEvent == toupcam.TOUPCAM_EVENT_IMAGE:
            ctx.CameraCallback(nEvent)

    def nextImage(self):
        self.waiting = True
        while self.waiting:
            time.sleep(0.00001)
        self.img_buffer = bytes(self.cam_buffer)
        image = np.frombuffer(self.img_buffer, dtype=np.uint8)
        image = np.flip(image.reshape((self.height, self.width, 3)),0)
        # print(f'pull image ok, size = {image.shape}')
        return image

    def CameraCallback(self, nEvent):
        if nEvent == toupcam.TOUPCAM_EVENT_IMAGE:
            print('callback')
            self.hcam.PullImageV2(self.cam_buffer, 24, None)
            self.waiting = False
        else:
            print('event callback: {}'.format(nEvent))


if __name__ == '__main__':
    cam = Cam()
    img = cam.get_image()
    plt.imshow(img)
    plt.show()


# class Camera(QtCore.QThread):
#     VideoSignal = QtCore.pyqtSignal(QtGui.QImage)
#
#     # vid_process_signal = QtCore.pyqtSignal('PyQt_PyObject')
#
#     def __init__(self, parent=None):
#         super(Camera, self).__init__(parent)
#         self.exposure = 200
#
#         # start micromanager and grab camera
#         mm_directory = 'C:\\Program Files\\Micro-Manager-2.0gamma'
#         sys.path.append(mm_directory)
#         os.chdir(mm_directory)
#
#         import MMCorePy
#         self.mmc = MMCorePy.CMMCore()
#         self.mmc.setCircularBufferMemoryFootprint(1000)
#         print('initializing camera...')
#         self.mmc.loadDevice('camera', 'PCO_Camera', 'pco_camera')
#         self.mmc.initializeAllDevices()
#         self.mmc.setCameraDevice('camera')
#         properties = self.mmc.getDevicePropertyNames('camera')
#         for p in properties:
#             print(p, self.mmc.getProperty('camera', p), self.mmc.getAllowedPropertyValues('camera', p))
#         self.mmc.setProperty('camera', 'Exposure', self.exposure)
#         self.mmc.startContinuousSequenceAcquisition(1)
#         self.run_video = True
#         self.rotation = False
#         self.window_size = QtCore.QSize(2060, 2048) # original image size
#         self.image = np.zeros((2060, 2048))
#         self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
#                                      self.window_size.width(), QtGui.QImage.Format_Grayscale16)
#
#     def __del__(self):
#         print('closing camera...')
#         self.mmc.stopSequenceAcquisition()
#         self.mmc.reset()
#
#     @QtCore.pyqtSlot(QtCore.QSize, 'PyQt_PyObject')
#     def resize_slot(self, size, running):
#         # print('received resize')
#         self.image = np.zeros((2060, 2048))
#         self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
#                                      self.window_size.width(), QtGui.QImage.Format_Grayscale16)
#         self.VideoSignal.emit(self.qt_image)
#         if running:
#             self.run_video = False
#             time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
#         else:
#             self.window_size = size
#             self.run_video = True
#             self.startVideo()
#
#     @QtCore.pyqtSlot('PyQt_PyObject')
#     def set_exposure_slot(self, exposure):
#         self.exposure = exposure
#         self.mmc.setProperty('camera', 'Exposure', self.exposure)
#         print('exposure set:', self.exposure)
#
#     @QtCore.pyqtSlot()
#     def take_screenshot_slot(self):
#         cv2.imwrite('C:\\Users\\Mohamed\\Desktop\\Harrison\\Screenshots\\' + strftime('%Y_%m_%d_%H_%M_%S.png', time.gmtime()),
#                     self.image)
#
#     @QtCore.pyqtSlot()
#     def startVideo(self):
#         # print('starting video stream...')
#         time.sleep(.5)
#         count = 0
#         QtWidgets.QApplication.processEvents()
#         while self.run_video:
#             # TODO fix, if possible
#             time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
#             QtWidgets.QApplication.processEvents()
#             if self.mmc.getRemainingImageCount() > 0:
#                 try:
#                     img = self.mmc.getLastImage()
#                     # not necessary at the moment
#                     window_h = self.window_size.height()
#                     window_w = self.window_size.width()
#                     if self.rotation:
#                         img = cv2.rotate(img, cv2.cv2.ROTATE_90_COUNTERCLOCKWISE)
#                     self.image = np.copy(img)
#                     img = cv2.resize(img, (window_h, window_w))
#                     self.qt_image = QtGui.QImage(img.data, window_w, window_h,
#                                                  img.strides[0], QtGui.QImage.Format_Grayscale16)
#                     if self.run_video:
#                         self.VideoSignal.emit(self.qt_image)
#                 except Exception as e:
#                     print(f'camera dropped frame {count}, {e}')
#             else:
#                 count += 1
#                 print('Camera dropped frame:', count)
#             QtWidgets.QApplication.processEvents()
