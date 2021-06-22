import numpy as np
import os

class CameraToProjector():


    def __init__(self):
        fn = 'camera_projector_calibration.npz'
        fn = os.path.join(os.path.split(__file__)[0], fn)
        data = np.load(fn)
        self.calibration_data = data['data']
        self.roi = data['rect']
        ((self.left, self.top),(self.right,self.bottom)) = self.roi

    def convert(self,x,y):
        x = round(x)
        y = round(y)
        return self.calibration_data[y,x]

if __name__ == '__main__':
    cam2proj = CameraToProjector()
