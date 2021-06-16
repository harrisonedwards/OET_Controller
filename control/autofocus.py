from control.micromanager import Camera
from control.stage import PriorStage
import cv2, numpy as np
from matplotlib import pyplot as plt
from time import sleep

IMG_SIZE = np.array([2160,2560])
H,W = IMG_SIZE
COLS = 20
ROWS = 20

BRENNER_SETPOINT = 2e12
BRENNER_P = 8e-11

MIN_FOCUS = 18000
MAX_FOCUS = 19000

IN_FOCUS = 19950

FOCUS_STEP = 10
NUM_STEPS = int((MAX_FOCUS-MIN_FOCUS)/FOCUS_STEP)+1

NUM_REPEATS = 1

result = np.zeros((ROWS,COLS,NUM_STEPS))


if IMG_SIZE[0]%ROWS!=0:
    print('Invalid number of rows')
    exit(1)
if IMG_SIZE[1]%COLS!=0:
    print('Invalid number of columns')
    exit(1)

def normalized_variance_cuda(img, size=IMG_SIZE):
    H,W = size
    gray = cv2.cuda.cvtColor(img,cv2.COLOR_BGR2GRAY)
    sum = cv2.cuda.sum(gray)[0]
    mean = np.ones((H,W))
    mean *= sum/(H*W)
    mean_gpu = cv2.cuda_GpuMat()
    mean_gpu.upload(mean)
    gray = gray.convertTo(rtype=cv2.CV_64F, dst=gray)
    sub = cv2.cuda.subtract(gray, mean_gpu, dtype=cv2.CV_64F)
    square = cv2.cuda.multiply(sub, sub, dtype=cv2.CV_64F)
    square_sum = cv2.cuda.sum(square)[0]
    return square_sum
    #print(square_sum/(mean[0,0]*H*W))

def grid_normalized_variance_cuda(img, rows=ROWS, cols=COLS, h=H, w=W):
    norm_var = np.zeros((rows, cols))
    for row in range(rows):
        for col in range(cols):
            selected_rows = (int(h * (row / rows)), int(h * ((row + 1) / rows)))
            selected_cols = (int(w * (col / cols)), int(w * ((col + 1) / cols)))

            rect = cv2.cuda_GpuMat(img, selected_rows, selected_cols)
            norm_var[row, col] = normalized_variance_cuda(rect, (int(h / rows), int(w / cols)))
    return norm_var

def brenner_cuda(img, h=H, w=W):
    gray = cv2.cuda.cvtColor(img, cv2.COLOR_BGR2GRAY)
    border = cv2.cuda.copyMakeBorder(gray, top=0, bottom=0, left=0, right=2, borderType=cv2.BORDER_REPLICATE)
    cropw = (0, int(h))
    croph = (2, int(w + 2))
    border = cv2.cuda_GpuMat(border, cropw, croph)
    sub = cv2.cuda.subtract(border, gray, dtype=cv2.CV_64F)
    square = cv2.cuda.multiply(sub, sub, dtype=cv2.CV_64F)
    return cv2.cuda.sum(square)[0]

def grid_brenner_cuda(img, rows=ROWS, cols=COLS, h=H, w=W):
    brenner = np.zeros((rows, cols))
    gray = cv2.cuda.cvtColor(img, cv2.COLOR_BGR2GRAY)
    border = cv2.cuda.copyMakeBorder(gray,top=0,bottom=0,left=0,right=2,borderType=cv2.BORDER_REPLICATE)
    cropw = (0,int(h))
    croph = (2,int(w+2))
    border = cv2.cuda_GpuMat(border,cropw,croph)
    sub = cv2.cuda.subtract(border, gray, dtype=cv2.CV_64F)
    square = cv2.cuda.multiply(sub,sub,dtype=cv2.CV_64F)
    for row in range(rows):
        for col in range(cols):
            selected_rows = (int(h * (row / rows)), int(h * ((row + 1) / rows)))
            selected_cols = (int(w * (col / cols)), int(w * ((col + 1) / cols)))
            rect = cv2.cuda_GpuMat(square, selected_rows, selected_cols)
            brenner[row,col]=cv2.cuda.sum(rect)[0]

    return brenner

def brenner(img):
    return np.sum(np.square(img[:,2:]-img[:,:-2]))

def normalized_variance(img):
    return np.sum(np.square(img-np.mean(img)))

def get_brenner(camera):
    img = camera.img()
    while img is None:
        img = camera.img()

    wb = camera.white_balance(img)
    brenner = grid_brenner_cuda(wb, 1, 1)
    return brenner.item()

def hunting(scope, camera, focus, step, focus_range, calculate_variance=False):

    min_focus = int(focus-(focus_range/2))
    max_focus = int(focus+(focus_range/2))

    focuses = np.arange(min_focus,max_focus+step,step)

    scope.set_focus(focuses[0])

    brenners = []
    variances = []
    actual_focuses = [focuses[0]]
    images = []

    for step in focuses[1:]:
        actual_focuses.append(step)
        img = camera.nextImage()
        images.append(img)
        b = normalized_variance(img)
        if calculate_variance:
            variance = normalized_variance_cuda(img)
            variances.append(variance)
        brenners.append(b)
        try:
            scope.set_focus(step)
        except Exception as e:
            print(e)
            break

    if calculate_variance:
        variance = normalized_variance_cuda(img)
        variances.append(variance)
    img = camera.nextImage()
    brenners.append(normalized_variance(img))
    x = np.array(actual_focuses)
    y = np.array(brenners)
    z = np.array(variances)

    return x,y,images


def focus(scope, camera, current_focus, step, focus_range):
    x, y, _ = hunting(scope, camera, current_focus, step, focus_range)
    ymax = np.argmax(y)
    temp_step = step
    temp_range = focus_range
    counter = 0
    while ymax == len(y) - 1 or ymax == 0:
        counter+=1
        if counter == 4:
            raise Exception('Unable to focus')
        temp_step*=2
        temp_range*=2
        x, y, _ = hunting(scope, camera, current_focus, temp_step, temp_range)
        ymax = np.argmax(y)

    idx = [ymax - 1, ymax, ymax + 1]
    x_fit = x[idx]
    y_fit = y[idx]

    p = np.poly1d(np.polyfit(x_fit, np.reciprocal(y_fit), 2))
    xp = np.linspace(current_focus-(focus_range/2), current_focus+(focus_range/2), 1000)
    max_focus = xp[np.argmin(p(xp))]

    if counter>0:
        return focus(scope, camera, max_focus, step, focus_range)
    return max_focus

def in_focus_image(scope, camera, current_focus, step, focus_range):
    max_focus = focus(scope, camera, current_focus, step, focus_range)
    print(max_focus)
    scope.set_focus(max_focus)
    return camera.nextImage()

def get_plane(points):
    points = np.array(points)
    v1 = points[0] - points[1]
    v2 = points[2] - points[1]
    cp = np.cross(v1, v2)
    a, b, c = cp
    d = cp @ points[0]
    x, y, z = points[3]

    z_diff = abs(((d - a * x - b * y) / c) - z)

    return (a, b, c, d), z_diff

def find_focal_plane(stage,cam,coords):
    # for 4 coords (x,y) find max focus using focus()
    for i in range(4):
        point=coords[i]
        stage.move_absolute(point[0],point[1])
        sleep(0.2)
        max_focus=focus(stage, cam, point[2], 10, 100)
        stage.set_focus(max_focus)
        sleep(0.2)
        img = cam.nextImage()
        plt.imshow(img, cmap='gray')
        plt.show()
        coords[i][2]=max_focus
    print(coords)
    # then using get_plane(), return the plane (a,b,c,d)
    focal_plane,zd=get_plane(coords)
    print('Focal plane z difference: ',zd,'microns')
    if zd > 10:
        raise Exception('Focal plane z difference too high')
    np.save('control/autofocus_plane.npy')
    return focal_plane

def load_focal_plane():
    return np.load('control/autofocus_plane.npy')

def get_z_from_plane(x, y, tilt_plane):
    a, b, c, d = tilt_plane
    return (d - a * x - b * y) / c

if __name__ == '__main__':

    stage = PriorStage()
    cam = Camera()
    cam.setExposure(100)

    points = np.zeros([4, 3])
    points[0] = [-129863, 96567, -3285]
    points[1] = [-124317, 97679, -3285]
    points[2] = [-129268, 101704, -3285]
    points[3] = [-126530, 101064, -3285]
    focal_plane = find_focal_plane(stage,cam,points)

    for i in range(4):
        stage.move_absolute(points[i][0], points[i][1])
        plt.imshow(in_focus_image(stage, cam, -3285, 10, 100), cmap='gray')
        plt.show()


