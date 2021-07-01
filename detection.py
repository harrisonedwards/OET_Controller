import cv2
import numpy as np


def detect(img):
    # finds and fills the located robots
    structure = np.ones((5, 5))
    canny = np.copy(cv2.Canny(img, 0, 60))
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
    rho = np.sqrt(contour[:, 0] ** 2 + contour[:, 1] ** 2)
    val, bin_edges = np.histogram(theta, bins=50, range=[-np.pi, np.pi])
    bin_centers = bin_edges[:-1] + np.diff(bin_edges) / 2

    return np.nanmean(np.where(val == 0, bin_centers, np.nan))


def get_robot_control_mask(large_contours, detect):
    # get memory
    robot_control_mask, inner_circle_mask = np.zeros(detect.shape), np.zeros(detect.shape)
    large_contour_image = cv2.drawContours(np.copy(robot_control_mask), large_contours, -1, 1, -1)

    robot_angles = []
    contours_towards_center = []
    contour_range_border_limit = 200
    robot_center_radius = 70

    dilation_size = 20

    # for drawing detected robot direction:
    line_length = 200
    line_width = 20

    for contour in large_contours:
        # find centers
        M = cv2.moments(contour)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        # check that our contours are within acceptable limits, draw their circle if they are
        if cx > contour_range_border_limit and cx < large_contour_image.shape[0] - contour_range_border_limit:
            if cy > contour_range_border_limit and cy < large_contour_image.shape[1] - contour_range_border_limit:
                contours_towards_center.append(contour)
                cv2.circle(inner_circle_mask, (cx, cy), robot_center_radius, 1, -1)
                angle = get_robot_angle(contour, (cx, cy))

                # cv2.line(inner_circle_mask, (cx, cy), (cx + int(line_length*np.cos(angle)), cy + int(line_length*np.sin(angle))), 1, line_width)
                robot_angles.append(angle)

    # draw the contours on our control mask
    robot_control_mask = cv2.drawContours(robot_control_mask, contours_towards_center, -1, 1, -1)  # .astype(np.uint8)
    robot_control_mask = np.logical_or(inner_circle_mask, robot_control_mask).astype(np.uint8)

    # subtract a dilation from outside of the periphery
    dilation = np.copy(robot_control_mask)  # .astype(np.uint8)
    dilation = cv2.dilate(dilation, np.ones((dilation_size, dilation_size)))
    robot_control_mask -= dilation

    return robot_control_mask, contours_towards_center, robot_angles

def get_robot_control(img):
    # REMOVE WHEN MONOCHROME
    detected = detect(img)[:, :, 0]

    large_contours = get_large_contours(detected)

    robot_control_mask, contours_towards_center, robot_angles = get_robot_control_mask(large_contours, detected)

    return robot_control_mask, contours_towards_center, robot_angles