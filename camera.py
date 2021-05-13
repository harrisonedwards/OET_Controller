import os, sys, time
from time import strftime
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import cv2

class Camera(QtCore.QThread):
    VideoSignal = QtCore.pyqtSignal(QtGui.QImage)

    # vid_process_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(Camera, self).__init__(parent)
        self.exposure = 200

        # start micromanager and grab camera
        mm_directory = 'C:\\Program Files\\Micro-Manager-2.0gamma'
        sys.path.append(mm_directory)
        os.chdir(mm_directory)

        import MMCorePy
        self.mmc = MMCorePy.CMMCore()
        self.mmc.setCircularBufferMemoryFootprint(1000)
        print('initializing camera...')
        self.mmc.loadDevice('camera', 'PCO_Camera', 'pco_camera')
        self.mmc.initializeAllDevices()
        self.mmc.setCameraDevice('camera')
        properties = self.mmc.getDevicePropertyNames('camera')
        for p in properties:
            print(p, self.mmc.getProperty('camera', p), self.mmc.getAllowedPropertyValues('camera', p))
        self.mmc.setProperty('camera', 'Exposure', self.exposure)
        self.mmc.startContinuousSequenceAcquisition(1)
        self.run_video = True
        self.rotation = False
        self.window_size = QtCore.QSize(2060, 2048) # original image size
        self.image = np.zeros((2060, 2048))
        self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
                                     self.window_size.width(), QtGui.QImage.Format_Grayscale16)

    def __del__(self):
        print('closing camera...')
        self.mmc.stopSequenceAcquisition()
        self.mmc.reset()

    @QtCore.pyqtSlot(QtCore.QSize, 'PyQt_PyObject')
    def resize_slot(self, size, running):
        # print('received resize')
        self.image = np.zeros((2060, 2048))
        self.qt_image = QtGui.QImage(self.image.data, self.window_size.height(),
                                     self.window_size.width(), QtGui.QImage.Format_Grayscale16)
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
        self.exposure = exposure
        self.mmc.setProperty('camera', 'Exposure', self.exposure)
        print('exposure set:', self.exposure)

    @QtCore.pyqtSlot()
    def take_screenshot_slot(self):
        cv2.imwrite('C:\\Users\\Mohamed\\Desktop\\Harrison\\Screenshots\\' + strftime('%Y_%m_%d_%H_%M_%S.png', time.gmtime()),
                    self.image)

    @QtCore.pyqtSlot()
    def startVideo(self):
        # print('starting video stream...')
        time.sleep(.5)
        count = 0
        QtWidgets.QApplication.processEvents()
        while self.run_video:
            # TODO fix, if possible
            time.sleep(1 / self.exposure + .05)  # add extra time, see later if we can increase performance later
            QtWidgets.QApplication.processEvents()
            if self.mmc.getRemainingImageCount() > 0:
                try:
                    img = self.mmc.getLastImage()
                    # not necessary at the moment
                    window_h = self.window_size.height()
                    window_w = self.window_size.width()
                    if self.rotation:
                        img = cv2.rotate(img, cv2.cv2.ROTATE_90_COUNTERCLOCKWISE)
                    self.image = np.copy(img)
                    img = cv2.resize(img, (window_h, window_w))
                    self.qt_image = QtGui.QImage(img.data, window_w, window_h,
                                                 img.strides[0], QtGui.QImage.Format_Grayscale16)
                    if self.run_video:
                        self.VideoSignal.emit(self.qt_image)
                except Exception as e:
                    print(f'camera dropped frame {count}, {e}')
            else:
                count += 1
                print('Camera dropped frame:', count)
            QtWidgets.QApplication.processEvents()
