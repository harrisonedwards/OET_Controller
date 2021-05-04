import os, sys, time
from PyQt5 import QtCore, QtGui


class ShowVideo(QtCore.QObject):
    VideoSignal = QtCore.pyqtSignal(QtGui.QImage)
    # vid_process_signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None):
        super(ShowVideo, self).__init__(parent)

        # start micromanager and grab camera
        mm_directory = 'C:\\Program Files\\Micro-Manager-2.0gamma'
        sys.path.append(mm_directory)
        os.chdir(mm_directory)
        import MMCorePy
        self.mmc = MMCorePy.CMMCore()
        self.mmc.setCircularBufferMemoryFootprint(100)
        print('initializing camera...')
        self.mmc.loadDevice('camera', 'PCO_Camera', 'pco_camera')
        self.mmc.initializeAllDevices()
        self.mmc.setCameraDevice('camera')

        self.run_video = True
        # self.window_size = window_size

    def __del__(self):
        print('closing camera...')
        self.mmc.stopSequenceAcquisition()
        self.mmc.reset()

    @QtCore.pyqtSlot()
    def startVideo(self):
        while self.run_video:
            self.mmc.startContinuousSequenceAcquisition(1)
            print('starting video stream...')
            time.sleep(.5)
            count = 0
            while True:
                time.sleep(.1)
                if self.mmc.getRemainingImageCount() > 0:
                    img = self.mmc.getLastImage()
                    # not necessary at the moment
                    # self.vid_process_signal.emit(img.copy())

                    height, width = img.shape
                    qt_image = QtGui.QImage(img.data,
                                            width,
                                            height,
                                            img.strides[0],
                                            QtGui.QImage.Format_RGB888)
                    # qt_image = qt_image.scaled(self.window_size)
                    self.VideoSignal.emit(qt_image)
                else:
                    count += 1
                    print('Camera dropped frame:', count)