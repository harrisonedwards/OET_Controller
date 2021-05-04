import os, sys, time
from PyQt5 import QtCore, QtGui


class Camera(QtCore.QObject):
    VideoSignal = QtCore.pyqtSignal(QtGui.QImage)
    # vid_process_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(Camera, self).__init__(parent)
        self.exposure = 100

        # start micromanager and grab camera
        mm_directory = 'C:\\Program Files\\Micro-Manager-2.0gamma'
        sys.path.append(mm_directory)
        os.chdir(mm_directory)

        import MMCorePy
        self.mmc = MMCorePy.CMMCore()
        self.mmc.setCircularBufferMemoryFootprint(500)
        print('initializing camera...')
        self.mmc.loadDevice('camera', 'PCO_Camera', 'pco_camera')
        self.mmc.initializeAllDevices()
        self.mmc.setCameraDevice('camera')
        properties = self.mmc.getDevicePropertyNames('camera')
        for p in properties:
            print(p, self.mmc.getProperty('camera', p), self.mmc.getAllowedPropertyValues('camera', p))
        self.mmc.setProperty('camera', 'Exposure', self.exposure)
        self.run_video = True
        self.window_size = QtCore.QSize(2060, 2048)

    def __del__(self):
        print('closing camera...')
        self.mmc.stopSequenceAcquisition()
        self.mmc.reset()

    @QtCore.pyqtSlot(QtCore.QSize)
    def resize_slot(self, size):
        print('caught resize')
        self.window_size = size


    @QtCore.pyqtSlot()
    def startVideo(self):
        while self.run_video:
            self.mmc.startContinuousSequenceAcquisition(1)
            print('starting video stream...')
            time.sleep(.5)
            count = 0
            while True:
                # TODO fix, if possible
                time.sleep(1/self.exposure + .01) # add extra time, see later if we can increase performance later
                if self.mmc.getRemainingImageCount() > 0:
                    img = self.mmc.getLastImage()
                    # not necessary at the moment
                    # self.vid_process_signal.emit(img.copy())
                    height, width = img.shape
                    qt_image = QtGui.QImage(img.data,
                                            width,
                                            height,
                                            img.strides[0],
                                            QtGui.QImage.Format_Grayscale16)
                    qt_image = qt_image.scaled(self.window_size)
                    self.VideoSignal.emit(qt_image)
                else:
                    count += 1
                    print('Camera dropped frame:', count)