import cv2
import numpy as np


def detect(img):
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


def get_robot_control_mask(large_contours, detect, dilation_size, buffer_offset_size, objective):
    # get memory
    robot_control_mask, inner_circle_mask = np.zeros(detect.shape), np.zeros(detect.shape)
    large_contour_image = cv2.drawContours(np.copy(robot_control_mask), large_contours, -1, 1, -1)

    # probably needs more adjustment in the future, so will make a dict for now
    objective_calibration_dict = {'2x': [8, 4],
                                  '4x': [4, 2],
                                  '10x': [2, 1],
                                  '20x': [1, 1],
                                  '40x': [0.5, 1]}

    robot_angles = []
    contours_towards_center = []
    contour_range_border_limit = 100 * objective_calibration_dict[objective][1]
    robot_center_radius = 120 // objective_calibration_dict[objective][0]
    line_length = 200
    line_width = 20

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
                cv2.circle(inner_circle_mask, (cx, cy), robot_center_radius, 1, -1)
                angle = get_robot_angle(contour, (cx, cy))
                # cv2.line(inner_circle_mask, (cx, cy),
                # (cx + int(line_length*np.cos(angle)), cy + int(line_length*np.sin(angle))), 1, line_width)
                robot_angles.append(angle)

    # draw the contours on our control mask
    robot_control_mask = cv2.drawContours(robot_control_mask, contours_towards_center, -1, 1, -1)  # .astype(np.uint8)
    robot_control_mask = np.logical_or(inner_circle_mask, robot_control_mask).astype(np.uint8)
    robot_control_mask = cv2.dilate(robot_control_mask, np.ones((buffer_offset_size, buffer_offset_size)))

    # subtract a dilation from outside of the periphery
    dilation = np.copy(robot_control_mask)  # .astype(np.uint8)
    dilation = cv2.dilate(dilation, np.ones((dilation_size, dilation_size)))
    robot_control_mask -= dilation

    return robot_control_mask, contours_towards_center, robot_angles


def get_robot_control(img, dilation_size, buffer_offset_size, objective):
    detected = detect(img)

    large_contours = get_large_contours(detected)

    robot_control_mask, contours_towards_center, robot_angles = get_robot_control_mask(large_contours,
                                                                                       detected,
                                                                                       dilation_size,
                                                                                       buffer_offset_size,
                                                                                       objective)

    return robot_control_mask, contours_towards_center, robot_angles