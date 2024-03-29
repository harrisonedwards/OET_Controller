import cv2, os
import numpy as np
import logging
import tensorflow as tf
import time

# load ai model
model_loc = r'C:\Users\Mohamed\Desktop\Harrison\OET\cnn_models\8515_vaL_model_augmented_w_gfp_class_weighted2'
try:
    logging.info(f'loading AI detection model: {model_loc}\ntensorflow version: {tf.__version__}')
    u_net = tf.keras.models.load_model(model_loc)
    # blank inference to start the graph
    u_net.predict(np.zeros((1, 2060, 2044, 1)))
    logging.info('loaded AI detection model.')
except Exception as e:
    logging.warning(f'Failed to load AI detection model: {str(e)}')
    logging.warning(f'CURRENT DIR: {os.getcwd()}')


class MyMeanIOU(tf.keras.metrics.MeanIoU):

    def update_state(self, y_true, y_pred, sample_weight=None):
        return super().update_state(tf.argmax(y_true, axis=-1), tf.argmax(y_pred, axis=-1), sample_weight)


def change_model(model_loc):
    try:
        logging.info(f'loading AI detection model: {model_loc}\ntensorflow version: {tf.__version__}')
        if 'miou' in model_loc:
            u_net = tf.keras.models.load_model(model_loc, custom_objects={'MyMeanIOU': MyMeanIOU})
        else:
            u_net = tf.keras.models.load_model(model_loc)
        # blank inference to start the graph
        u_net.predict(np.zeros((1, 2060, 2044, 1)))
        logging.info('loaded AI detection model.')
    except Exception as e:
        logging.warning(f'Failed to load AI detection model: {str(e)}')
        logging.warning(f'CURRENT DIR: {os.getcwd()}')


def get_cell_overlay(img):
    img = np.expand_dims(img, 0)
    if len(img.shape) < 4:
        img = np.expand_dims(img, -1)

    t0 = time.time()
    pred_mask = u_net.predict(img)
    print(f'inference time: {time.time() - t0}')
    pred_mask = tf.argmax(pred_mask, axis=-1)

    red_mask = tf.where(pred_mask == 1, 255, 0)
    green_mask = tf.where(pred_mask == 2, 255, 0)

    cell_detection_overlay = tf.stack((red_mask, green_mask, np.zeros(red_mask.shape)), axis=-1)
    cell_detection_overlay = tf.squeeze(cell_detection_overlay)

    cell_detection_overlay = tf.image.resize(cell_detection_overlay, (2048, 2060)).numpy().astype(np.uint8)
    return cell_detection_overlay


def detect_robots(img):
    # finds and fills the located robots
    img = cv2.convertScaleAbs(img, 1, 1.5)
    structure = np.ones((3, 3))
    canny = np.copy(cv2.Canny(img, 20, 120))
    dilated = cv2.dilate(canny, structure)
    contours, hier = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    filled = cv2.drawContours(np.zeros(img.shape, dtype=np.uint8), contours, -1, 1, -1, 0, hier, 1)
    return np.copy(filled)


def get_large_contours(detect):
    # take a detection mask, and contour information add circles
    contours, hier = cv2.findContours(detect, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    large_contours = []
    contour_area_minimum = 2000
    for c in contours:
        if cv2.contourArea(c) > contour_area_minimum:
            large_contours.append(c)

    return large_contours


def get_robot_angle(contour, center):
    contour = np.squeeze(np.copy(contour))
    contour -= center
    theta = np.arctan2(contour[:, 1], contour[:, 0])
    # rho = np.sqrt(contour[:, 0] ** 2 + contour[:, 1] ** 2)
    val, bin_edges = np.histogram(theta, bins=50, range=[-np.pi, np.pi])
    bin_centers = bin_edges[:-1] + np.diff(bin_edges) / 2

    return np.nanmean(np.where(val == 0, bin_centers, np.nan))


def get_robots(large_contours, detect, objective):
    # get memory
    robot_control_mask = np.zeros(detect.shape)
    large_contour_image = cv2.drawContours(np.copy(robot_control_mask), large_contours, -1, 1, -1)

    # probably needs more adjustment in the future, so will make a dict for now
    objective_calibration_dict = {'2x': 4,
                                  '4x': 2,
                                  '10x': 1,
                                  '20x': 1,
                                  '40x': 1}

    robot_angles = []
    contours_towards_center = []
    contour_range_border_limit = 100 * objective_calibration_dict[objective]

    contours_in_limits = []
    for contour in large_contours:
        xs = np.squeeze(contour)[:, 0]
        ys = np.squeeze(contour)[:, 1]
        # check that our contours are within acceptable limits, draw their circle if they are
        if np.all(xs > contour_range_border_limit) and np.all(
                xs < large_contour_image.shape[0] - contour_range_border_limit):
            if np.all(ys > contour_range_border_limit) and np.all(
                    ys < large_contour_image.shape[0] - contour_range_border_limit):
                contours_in_limits.append(contour)
                M = cv2.moments(contour)
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                contours_towards_center.append(contour)

                angle = get_robot_angle(contour, (cx, cy))
                robot_angles.append(angle)

    return contours_towards_center, robot_angles


def get_robot_control(img, objective):
    detected = detect_robots(img)

    large_contours = get_large_contours(detected)

    robots, robot_angles = get_robots(large_contours,
                                      detected,
                                      objective)
    return robots, robot_angles
