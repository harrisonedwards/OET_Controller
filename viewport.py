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
    VideoSignal = QtCore.pyqtSignal(QtGui.QImage)

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
        self.window_size = QtCore.QSize(self.height, self.width)  # original image size
        self.image = np.zeros((self.height, self.width))
        self.robot_control_mask = np.zeros((self.height, self.width)).astype(np.uint8)
        self.path_overlay = np.zeros((self.height, self.width)).astype(np.uint8)
        self.detection_overlay = np.zeros((self.height, self.width)).astype(np.uint8)
        self.qt_image = QtGui.QImage(self.image.data, self.height,
                                     self.width, QtGui.QImage.Format_Grayscale16)

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
                    self.process_and_emit_image(img)
                except Exception as e:
                    print(f'camera dropped frame {count}, {e}')
            else:
                count += 1
                print('Camera dropped frame:', count)
            QtWidgets.QApplication.processEvents()

    def process_and_emit_image(self, np_img):
        # for screenshots:
        # self.image = np.copy(np_img)

        if self.detection:
            if self.detection_overlay.shape[-1] != 3:
                self.detection_overlay = cv2.cvtColor(self.detection_overlay, cv2.COLOR_GRAY2BGR)
                # make it red only
                self.detection_overlay[:, :, 1:] = 0
            np_img = cv2.addWeighted(np_img, 1, self.detection_overlay, 0.5, 0)
            np_img = cv2.addWeighted(np_img, 1, self.path_overlay, 0.5, 0)

        window_h = self.window_size.height()
        window_w = self.window_size.width()

        # self.image = np.copy(np_img)

        self.resize_lock.lock()

        if self.rotation:
            np_img = cv2.rotate(np_img, cv2.cv2.ROTATE_90_COUNTERCLOCKWISE)

        np_img = cv2.resize(np_img, (window_h, window_w))
        self.qt_image = QtGui.QImage(np_img.data, window_w, window_h,
                                     np_img.strides[0], QtGui.QImage.Format_Grayscale16)

        self.resize_lock.unlock()
        if self.run_video:
            self.VideoSignal.emit(self.qt_image)


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


