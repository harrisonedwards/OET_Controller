import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
import cv2, os
from skimage import util
import numpy as np
from functools import partial
from timeit import default_timer as timer
import time
from logs import LogWriter
from PyQt5 import QtCore,QtGui,QtWidgets
class MicroManager():
    
    def __init__(self):
        
        # Append MM directory to path
        import sys,os
        mm_directory = 'C:\\Program Files\\Micro-Manager-2.0gamma'
        sys.path.append(mm_directory)
        system_cfg_file = os.path.join(mm_directory,'ham.cfg')

        # For most devices it is unnecessary to change to the MM direcotry prior to importing, but in some cases (such as the pco.de driver), it is required.

        prev_dir = os.getcwd()
        os.chdir(mm_directory) # MUST change to micro-manager directory for method to work
        import MMCorePy

        # Get micro-manager controller object
        self.mmc = MMCorePy.CMMCore()

        # Load system configuration (loads all devices)
        self.mmc.loadSystemConfiguration(system_cfg_file)
        os.chdir(prev_dir)


class ProcessWorker(QtCore.QObject):
    imageChanged = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self,cam):
        super().__init__()

        self.cam = cam
        self.running = True

    def doWork(self):

        while self.running:
            frame = self.cam.next_image()
            frame = (frame/65535)*255
            rgbImage = cv2.cvtColor(frame.astype(np.uint8),cv2.COLOR_GRAY2BGR)
            # h, w, ch = rgbImage.shape
            # bytesPerLine = ch * w
            # convertToQtFormat = QtGui.QImage(rgbImage.data, w, h, bytesPerLine, QtGui.QImage.Format_RGB888)
            self.imageChanged.emit(rgbImage)
        self.thread().quit()

class Camera():

    height = 0
    width = 0

    def __init__(self):
        mm = MicroManager()
        self.mmc = mm.mmc
        self.mmc.setCameraDevice('HamamatsuHam_DCAM')
        self.set_exposure(16.6)
        self.mmc.setCircularBufferMemoryFootprint(8) # set memory buffer to size of 1 image so that we always have the latest image
        self.mmc.startContinuousSequenceAcquisition(1)
        img = self.next_image()
        self.height, self.width = img.shape
        self.stop_capture = False
        self.balance_image = cv2.imread('camera/balance_img.png',-1)
        self.times = []
        self.countcheck = 0
        self.tpe = ThreadPoolExecutor(1)

    def intensity_balance(self,img):
        img = img/self.balance_image
        img = img/np.max(img)
        return util.img_as_float(img)

    def next_image(self):
        while self.mmc.getRemainingImageCount() == 0:
            time.sleep(0.001)
        return self.mmc.popNextImage()#self.mmc.getLastImage()

    def set_exposure(self, exposure):
        self.mmc.setProperty('HamamatsuHam_DCAM','Exposure',exposure)

    def view(self,img, scaling=0.5):
        cv2.imshow('Viewer',cv2.resize(img,(0,0),fx=scaling,fy=scaling))
        cv2.waitKey(1)

    def write(self, img, fn, bit_depth=16):
        if bit_depth==8:
            img = cv2.normalize(img,None,alpha=0,beta=255,norm_type=cv2.NORM_MINMAX,dtype=cv2.CV_8U)
        cv2.imwrite(fn,img)


    def _capture_sequence(self, folder, prefix, viewer=False, bit_depth=16, offline=False, threads=8):
        if offline:
            frames = []
        saver = ThreadPoolExecutor(threads)
        if viewer:
            viewer_thread = ThreadPoolExecutor(1)
        log = LogWriter(os.path.join(folder,f'{prefix}_camera.log'))
        counter = 0
        self.mmc.clearCircularBuffer()
        while not self.stop_capture:
            img = self.next_image()
            fn = f'{prefix}_{counter}.png'
            log.write(timer(),fn)
            if offline:
                frames.append(img)
            else:
                saver.submit(partial(self.write, img, os.path.join(folder, fn), bit_depth))
            if viewer:
                viewer_thread.submit(partial(self.view,img))
            counter+=1

        self.stop_capture = False
        if offline:
            for i,frame in enumerate(frames):
                fn = f'{prefix}_{i}.png'
                saver.submit(partial(self.write, frame, os.path.join(folder, fn), bit_depth))
        if viewer:
            viewer_thread.shutdown()
        saver.shutdown(wait=True)

    def capture_sequence(self, folder, prefix, viewer=False, bit_depth=16, offline=False, threads=8):
        self.tpe.submit(partial(self._capture_sequence, folder, prefix, viewer, bit_depth, offline, threads))

    def stop_sequence(self):
        self.stop_capture = True
        self.tpe.shutdown(wait=True)
        self.tpe = ThreadPoolExecutor(1)

    def start_sequence_qt(self,callback_function):
        self.workerThread = QtCore.QThread()
        self.worker = ProcessWorker(self)
        self.worker.moveToThread(self.workerThread)
        self.workerThread.finished.connect(self.worker.deleteLater)
        self.workerThread.started.connect(self.worker.doWork)
        self.worker.imageChanged.connect(callback_function)
        self.workerThread.start()

    def stop_sequence_qt(self):
        self.worker.running = False
        self.workerThread.wait()

    def Close(self):
        self.stop_sequence_qt()

if __name__ == '__main__':
    def view(img):
        cv2.imshow('next image', c.next_image())
        cv2.waitKey(1)

    c = Camera()
    c.start_sequence_with_callback(view)
    time.sleep(5)
    c.set_exposure(100)
    time.sleep(5)
    c.stop_sequence()


