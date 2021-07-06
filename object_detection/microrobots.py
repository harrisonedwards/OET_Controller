# from smallestenclosingcircle import make_circle

import cv2

import matplotlib
import matplotlib.pyplot as plt

import numpy as np

import pathlib

from scipy import optimize

import scipy.ndimage as ndi

from skimage import draw
from skimage import exposure
from skimage import feature
from skimage import filters
from skimage import io
from skimage import measure
from skimage import morphology
from skimage import segmentation
from skimage import util

import sys

import time

matplotlib.use('TkAgg')


def clear_border(ar, return_binary=False):
    ar_label, _ = ndi.label(ar)
    out = segmentation.clear_border(ar_label)

    if return_binary:
        out = np.array(out, dtype=bool)

    return out


def remove_large_objects(ar, max_size, connectivity=1):
    out = np.copy(ar)

    sel = ndi.generate_binary_structure(ar.ndim, connectivity)
    ccs = np.zeros_like(ar, dtype=np.int32)
    ndi.label(ar, sel, output=ccs)

    ccs_sizes = np.bincount(ccs.ravel())
    too_large = ccs_sizes > max_size
    too_large_mask = too_large[ccs]
    out[too_large_mask] = 0

    return out


def keep_largest_object(ar, connectivity=2):
    out = np.copy(ar)

    sel = ndi.generate_binary_structure(ar.ndim, connectivity)
    ccs = np.zeros_like(ar, dtype=np.int32)
    ndi.label(ar, sel, output=ccs)

    ccs_sizes = np.bincount(ccs.ravel())
    ccs_sizes[ccs_sizes == np.max(ccs_sizes)] = 0
    smaller = ccs_sizes != np.max(ccs_sizes)
    smaller_mask = smaller[ccs]
    out[smaller_mask] = 0

    return out


def compute_branch_points(skeleton):
    num_branches = 0

    for i in range(1, skeleton.shape[0] - 1):
        for j in range(1, skeleton.shape[1] - 1):

            if skeleton[i, j] == 255:

                tmp = np.copy(skeleton[i - 1:i + 2, j - 1:j + 2])
                tmp[1, 1] = 0

                ncc, _ = cv2.connectedComponents(tmp, connectivity=4)

                if ncc > 3:
                    num_branches += ncc - 3

    return num_branches


def separate_branches(skeleton):
    out = np.copy(skeleton)
    num_branches = 0

    for i in range(1, skeleton.shape[0] - 1):
        for j in range(1, skeleton.shape[1] - 1):

            if skeleton[i, j] == 255:

                tmp = np.copy(skeleton[i - 1:i + 2, j - 1:j + 2])
                tmp[1, 1] = 0

                ncc, _ = cv2.connectedComponents(tmp, connectivity=4)

                if ncc > 3:
                    out[i - 1:i + 2, j - 1:j + 2] = 0
                    num_branches += ncc - 3

    return out, num_branches


def line(x, a, b):
    return a * x + b


def compute_angle(vec1, vec2):
    vec1_unit = vec1 / np.linalg.norm(vec1, ord=2)
    vec2_unit = vec2 / np.linalg.norm(vec2, ord=2)

    return np.arccos(np.clip(np.dot(vec1_unit, vec2_unit), -1.0, 1.0))


def compute_vector_parameters(vec):
    angle = compute_angle(np.array([1, 0]), vec)
    angle = angle if vec[1] >= 0 else -angle

    return np.linalg.norm(vec, ord=2), angle


def draw_microrobot(image, x_center, y_center, radius, angle, as_mask, draw_value=0):
    x_center = int(x_center)
    y_center = int(y_center)
    radius = int(radius)

    if as_mask:
        radius += 10
        rr, cc = draw.disk((y_center, x_center), int(radius), shape=image.shape)
        image[rr, cc] = draw_value
        return image

    grayscale = False
    if len(image.shape) == 2:
        grayscale = True

    rr, cc = draw.disk((y_center, x_center), 2, shape=image.shape)

    if grayscale:
        image[rr, cc] = draw_value
    else:
        image[rr, cc] = (1, 0, 0)

    rr, cc = draw.circle_perimeter(y_center, x_center, radius, shape=image.shape)

    if grayscale:
        image[rr, cc] = draw_value
    else:
        image[rr, cc] = (1, 0, 0)

    x_end_ori = x_center + int(np.cos(angle) * radius)
    y_end_ori = y_center + int(np.sin(angle) * radius)

    rr, cc = draw.line(y_center, x_center, y_end_ori, x_end_ori)

    idx_cur = 0
    idx_end = len(rr)
    while idx_cur < idx_end:
        if rr[idx_cur] < 0 or rr[idx_cur] >= image.shape[0] or \
                cc[idx_cur] < 0 or cc[idx_cur] >= image.shape[1]:
            rr = np.delete(rr, idx_cur)
            cc = np.delete(cc, idx_cur)
            idx_cur -= 1
            idx_end -= 1
        idx_cur += 1

    if grayscale:
        image[rr, cc] = draw_value
    else:
        image[rr, cc] = (1, 0, 0)

    return image


def draw_microrobots(image, robots, as_mask, draw_value=255, thickness=5):
    for i in range(0, robots.shape[0]):
        image = draw_microrobot(image, robots[i, 0], robots[i, 1], robots[i, 2], robots[i, 3], as_mask, draw_value)
    image = cv2.dilate(image,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(thickness,thickness)))
    return image


def output_microrobots(robots, filename, output_directory):
    robots_txt = ''
    for i in range(0, robots.shape[0]):
        robots_txt += f'{robots[i, 0]};{robots[i, 1]};{robots[i, 2]};{robots[i, 3]}\n'

    f = open(pathlib.Path(output_directory, f'{filename}_microrobots.txt'), 'w')
    f.write(robots_txt)
    f.close()

    np.savez_compressed(pathlib.Path(output_directory, f'{filename}_microrobots'), robots)


def check_blob_conformity(image):
    label, _ = ndi.label(image)
    blobs = measure.regionprops(label)
    blob = blobs[0]

    # ---------- Computing shape characteristics ----------

    axis_ratio = blob.major_axis_length / blob.minor_axis_length
    centroid_x = int(blob.centroid[1])
    centroid_y = int(blob.centroid[0])

    # print(f'axis_ratio: {axis_ratio}')
    # print(f'blob_solidity: {blob.solidity}')
    # print(f'image_centroid: {image[centroid_y, centroid_x]}')

    if axis_ratio > 1.30:
        return False

    if blob.solidity < 0.45 or blob.solidity > 0.75:
        return False

    if image[centroid_y, centroid_x] > 0:
        return False

    # ---------- Computing the number of branches (legs) ----------

    skeleton = morphology.skeletonize(image, method='lee')

    num_branches = compute_branch_points(skeleton)

    # print(f'num_branches: {num_branches}')

    if num_branches < 5:
        return False

    return True


def compute_microrobot_parameters(r_img, r_pos, r_num, filename, output_directory, output_results):
    label, _ = ndi.label(r_img)
    robots = measure.regionprops(label)
    robot = robots[0]

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_b{r_num}_0_robot.png'), r_img, cmap='gray')
        # plt.imshow(r_img, cmap='gray')
        # plt.show()

    # ---------- Inversion ----------

    r_inv = np.logical_not(r_img)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_r{r_num}_1_inverse.png'), r_inv, cmap='gray')
        # plt.imshow(r_inv, cmap='gray')
        # plt.show()

    # ---------- Skeletonization of the inverse image ----------

    r_inv = util.img_as_ubyte(r_inv)
    r_inv = cv2.copyMakeBorder(r_inv, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=255)
    skeleton = morphology.skeletonize(r_inv, method='lee')

    # skeleton = cv2.ximgproc.thinning(r_inv, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_r{r_num}_2_skeleton.png'), skeleton, cmap='gray')
        # plt.imshow(skeleton, cmap='gray')
        # plt.show()

    # ---------- Contour detection and suppression ----------

    skeleton = util.img_as_ubyte(skeleton)
    contours, _ = cv2.findContours(skeleton, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    fragments = cv2.drawContours(skeleton, contours, 0, 0, 0)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_r{r_num}_3_fragments.png'), fragments, cmap='gray')
        # plt.imshow(fragments, cmap='gray')
        # plt.show()

    # ---------- Raw axis retrieval ----------

    raw_axis = keep_largest_object(fragments)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_r{r_num}_4_raw_axis.png'), raw_axis, cmap='gray')
        # plt.imshow(raw_axis, cmap='gray')
        # plt.show()

    # ---------- Separate branches ----------

    # raw_axis, num_branches = separate_branches(raw_axis)
    #
    # if num_branches > 0:
    #     raw_axis = keep_largest_object(raw_axis)
    #
    # if output_result:
    #     plt.imsave(pathlib.Path(output_directory, f'{filename}_b{r_num}_5_raw_axis_trim.png'), raw_axis, cmap='gray')
    #     # plt.imshow(raw_axis, cmap='gray')
    #     # plt.show()

    # ---------- Line fit on raw axis ----------

    indexes = np.where(raw_axis != 0)

    popt_x, pcov_x = optimize.curve_fit(line, indexes[1], indexes[0])
    popt_y, pcov_y = optimize.curve_fit(line, indexes[0], indexes[1])

    perr_x = np.sqrt(np.diag(pcov_x))
    perr_y = np.sqrt(np.diag(pcov_y))

    optimize_x = True

    if perr_x[0] > perr_y[0]:
        optimize_x = False

    # if optimize_x:
    #     print('slope x (y = ax + b): ', popt_x[0])
    # else:
    #     print('slope y (x = ay + b): ', popt_y[0])

    # ---------- Compute circumcircle ----------

    # cx, cy, r = make_circle(robot.coords)

    # ---------- Compute orientation from centroids ----------

    sel = ndi.generate_binary_structure(raw_axis.ndim, 2)
    raw_axis_label, _ = ndi.label(raw_axis, sel)

    raw_axis_blob = measure.regionprops(raw_axis_label)
    raw_axis_center = raw_axis_blob[0].centroid

    raw_axis_dx = robot.centroid[1] - raw_axis_center[1]
    raw_axis_dy = robot.centroid[0] - raw_axis_center[0]

    # raw_axis_dx = cx - raw_axis_center[1]
    # raw_axis_dy = cy - raw_axis_center[0]

    top, bottom, left, right = False, False, False, False

    if raw_axis_dx < 0:
        right = True
    else:
        left = True
    if raw_axis_dy < 0:
        bottom = True
    else:
        top = True

    vec_orientation = []

    if optimize_x:
        if top and left:
            vec_orientation = [-1, -popt_x[0]]
        if top and right:
            vec_orientation = [1, popt_x[0]]
        if bottom and left:
            vec_orientation = [-1, -popt_x[0]]
        if bottom and right:
            vec_orientation = [1, popt_x[0]]
    else:
        if top and left:
            vec_orientation = [-popt_y[0], -1]
        if top and right:
            vec_orientation = [-popt_y[0], -1]
        if bottom and left:
            vec_orientation = [popt_y[0], 1]
        if bottom and right:
            vec_orientation = [popt_y[0], 1]

    norm_vec = np.linalg.norm(vec_orientation, ord=2)
    vec_orientation = vec_orientation / norm_vec

    _, angle = compute_vector_parameters(vec_orientation)

    # print(f'angle: {angle * 180 / np.pi}')

    # ---------- Compute center coordinates on image and radius ----------

    h_width = int(r_img.shape[1] / 2)
    h_height = int(r_img.shape[0] / 2)

    x_center = int(r_pos[1] + h_width)
    y_center = int(r_pos[0] + h_height)

    radius = h_width if h_width > h_height else h_height

    # x_center = int(x_pos + cx)
    # y_center = int(y_pos + cy)

    # radius = int(r)

    # print(f'x_center: {x_center} y_center: {y_center} radius: {radius}')

    return x_center, y_center, radius, angle


def detect_microrobots_intensity(image, filename, output_directory, root_directory, output_results):
    grayscale = False
    if len(image.shape) == 2:
        grayscale = True

    out_num = 0

    if output_results:
        if grayscale:
            plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_original.png'), image, cmap='gray')
            # plt.imshow(image, cmap='gray')
            # plt.show()
        else:
            plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_original.png'), image)
            # plt.imshow(image)
            # plt.show()
        out_num += 1

    # ---------- Grayscale conversion ----------

    if grayscale:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_gray.png'), gray, cmap='gray')
        # plt.imshow(gray, cmap='gray')
        # plt.show()
        out_num += 1

    # ---------- Filtering ----------

    # filtered = exposure.equalize_adapthist(gray)
    filtered = exposure.adjust_gamma(gray, 0.3)
    filtered = filters.gaussian(filtered)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_filtered.png'), filtered, cmap='gray')
        # plt.imshow(filtered, cmap='gray')
        # plt.show()
        out_num += 1

    # ---------- Thresholding ----------

    thr = filters.threshold_local(filtered, 63)
    thr = filtered > thr

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_threshold.png'), thr, cmap='gray')
        # plt.imshow(thr, cmap='gray')
        # plt.show()
        out_num += 1

    # ---------- Morphological operations ----------

    morpho = util.img_as_ubyte(thr)

    # *** U of T images ***

    # morpho = cv2.morphologyEx(morpho, cv2.MORPH_OPEN, morphology.disk(2),
    #                           borderType=cv2.BORDER_CONSTANT, borderValue=0)
    # morpho = cv2.morphologyEx(morpho, cv2.MORPH_CLOSE, morphology.disk(2),
    #                           borderType=cv2.BORDER_CONSTANT, borderValue=0)

    # *** UCL images ***

    morpho = cv2.morphologyEx(morpho, cv2.MORPH_OPEN, morphology.disk(1),
                              borderType=cv2.BORDER_CONSTANT, borderValue=0)
    morpho = cv2.morphologyEx(morpho, cv2.MORPH_CLOSE, morphology.disk(1),
                              borderType=cv2.BORDER_CONSTANT, borderValue=0)

    morpho = np.array(morpho, dtype=bool)
    morpho = morphology.remove_small_objects(morpho, 500)
    morpho = remove_large_objects(morpho, 10000, 2)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_morpho.png'), morpho, cmap='gray')
        # plt.imshow(morpho, cmap='gray')
        # plt.show()
        out_num += 1

    robot_count = 0
    robots = np.zeros((0, 4), dtype=float)
    robots_mask = np.zeros(image.shape[:2], dtype=bool)

    morpho_labels, _ = ndi.label(morpho)
    blobs = measure.regionprops(morpho_labels)

    for blob in blobs:
        # ---------- Morphological operations on blobs ----------

        blob_morpho = ndi.binary_fill_holes(blob.image)
        blob_morpho = util.img_as_ubyte(blob_morpho)

        # *** U of T images ***

        # se = 15

        # *** UCL images ***

        se = 5

        blob_morpho = cv2.copyMakeBorder(blob_morpho, se, se, se, se, cv2.BORDER_CONSTANT, value=0)
        blob_morpho = cv2.dilate(blob_morpho, morphology.disk(se))
        blob_morpho = ndi.binary_fill_holes(blob_morpho)

        # ---------- Discarding non-conform blobs ----------

        if not check_blob_conformity(blob_morpho):
            continue

        robot_count += 1

        # ---------- Update robots mask ----------

        x_pos = blob.bbox[1] - se
        y_pos = blob.bbox[0] - se

        width = blob_morpho.shape[1]
        height = blob_morpho.shape[0]

        x_min_offset = 0
        x_max_offset = 0
        y_min_offset = 0
        y_max_offset = 0

        if x_pos < 0:
            x_min_offset = -x_pos
        if x_pos + width >= robots_mask.shape[1]:
            x_max_offset = x_pos + width - robots_mask.shape[1]
        if y_pos < 0:
            y_min_offset = -y_pos
        if y_pos + height >= robots_mask.shape[0]:
            y_max_offset = y_pos + height - robots_mask.shape[0]

        x_min_mask = x_pos + x_min_offset
        x_max_mask = x_pos + width - x_max_offset
        y_min_mask = y_pos + y_min_offset
        y_max_mask = y_pos + height - y_max_offset

        x_min_blob = x_min_offset
        x_max_blob = width - x_max_offset
        y_min_blob = y_min_offset
        y_max_blob = height - y_max_offset

        np.putmask(robots_mask[y_min_mask: y_max_mask, x_min_mask: x_max_mask],
                   blob_morpho[y_min_blob: y_max_blob, x_min_blob: x_max_blob], True)

        # ---------- Compute robot parameters ----------

        x_center, y_center, radius, angle = compute_microrobot_parameters(blob_morpho, (y_pos, x_pos), robot_count,
                                                                          filename, output_directory, output_results)

        radius += 5

        tmp_robot = np.zeros((1, 4), dtype=float)
        tmp_robot[0][0] = x_center
        tmp_robot[0][1] = y_center
        tmp_robot[0][2] = radius
        tmp_robot[0][3] = angle

        robots = np.vstack((robots, tmp_robot))

    # ---------- Dilate mask for better coverage ----------

    robots_mask = util.img_as_ubyte(robots_mask)
    robots_mask = cv2.dilate(robots_mask, morphology.disk(10))
    robots_mask = np.array(robots_mask, dtype=bool)

    # ---------- Overlay mask on original image ----------

    # mask_removed = np.copy(image)
    # mask_removed[robots_mask] = 0
    # plt.imshow(mask_removed, cmap='gray')
    # plt.show()

    # ---------- Output results ----------

    if output_results:
        robots_labelled = np.copy(image)
        robots_labelled = draw_microrobots(robots_labelled, robots, False)

        if grayscale:
            plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_microrobots_labelled.png'),
                       robots_labelled, cmap='gray')
            plt.imsave(pathlib.Path(root_directory, f'{filename}_microrobots_labelled.png'),
                       robots_labelled, cmap='gray')
            # plt.imshow(robots_labelled, cmap='gray')
            # plt.show()
        else:
            plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_microrobots_labelled.png'),
                       robots_labelled)
            plt.imsave(pathlib.Path(root_directory, f'{filename}_microrobots_labelled.png'),
                       robots_labelled)
            # plt.imshow(robots_labelled)
            # plt.show()

        output_microrobots(robots, filename, output_directory)

    return robots, robots_mask


def detect_microrobots_edges(image, filename, output_directory, root_directory, output_results):
    grayscale = False
    if len(image.shape) == 2:
        grayscale = True

    out_num = 0

    if output_results:
        if grayscale:
            plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_original.png'), image, cmap='gray')
            # plt.imshow(image, cmap='gray')
            # plt.show()
        else:
            plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_original.png'), image)
            # plt.imshow(image)
            # plt.show()
        out_num += 1

    # ---------- Grayscale conversion ----------

    if grayscale:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_gray.png'), gray, cmap='gray')
        # plt.imshow(gray, cmap='gray')
        # plt.show()
        out_num += 1

    # ---------- Filtering ----------

    filtered = exposure.equalize_adapthist(gray)

    if output_results:
        # plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_filtered.png'), filtered, cmap='gray')
        # plt.imshow(filtered, cmap='gray')
        plt.show()
        out_num += 1

    # ---------- Edge detection ----------

    edge = feature.canny(filtered, sigma=3)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_edges.png'), edge, cmap='gray')
        # plt.imshow(edge, cmap='gray')
        # plt.show()
        out_num += 1

    # ---------- Morphological operations ----------

    edge_morpho = util.img_as_ubyte(edge)
    edge_morpho = cv2.morphologyEx(edge_morpho, cv2.MORPH_CLOSE, morphology.disk(1),
                                   borderType=cv2.BORDER_CONSTANT, borderValue=0)
    edge_morpho = ndi.binary_fill_holes(edge_morpho)
    edge_morpho = clear_border(edge_morpho, True)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_edges_morpho.png'), edge_morpho, cmap='gray')
        # plt.imshow(edge_morpho, cmap='gray')
        # plt.show()
        out_num += 1

    morpho = np.array(edge_morpho, dtype=bool)
    morpho = morphology.remove_small_objects(morpho, 500)
    morpho = remove_large_objects(morpho, 10000, 2)

    if output_results:
        plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_morpho.png'), morpho, cmap='gray')
        # plt.imshow(morpho, cmap='gray')
        # plt.show()
        out_num += 1

    robot_count = 0
    robots = np.zeros((0, 4), dtype=float)
    robots_mask = np.zeros(image.shape, dtype=bool)

    morpho_labels, _ = ndi.label(morpho)
    blobs = measure.regionprops(morpho_labels)

    for blob in blobs:

        # ---------- Discarding non-conform blobs ----------

        if not check_blob_conformity(blob.image):
            continue

        robot_count += 1

        # ---------- Update robots mask ----------

        x_pos = blob.bbox[1]
        y_pos = blob.bbox[0]

        np.putmask(robots_mask[blob.bbox[0]: blob.bbox[2], blob.bbox[1]: blob.bbox[3]], blob.image, True)

        # ---------- Compute robot parameters ----------

        x_center, y_center, radius, angle = compute_microrobot_parameters(blob.image, (y_pos, x_pos),
                                                                          robot_count, filename, output_directory,
                                                                          output_results)

        tmp_robot = np.zeros((1, 4), dtype=float)
        tmp_robot[0][0] = x_center
        tmp_robot[0][1] = y_center
        tmp_robot[0][2] = radius
        tmp_robot[0][3] = angle

        robots = np.vstack((robots, tmp_robot))

    # ---------- Overlay mask on original image ----------

    # mask_removed = np.copy(image)
    # mask_removed[robots_mask] = 0
    # plt.imshow(mask_removed, cmap='gray')
    # plt.show()

    # ---------- Output results ----------

    if output_results:
        robots_labelled = np.copy(image)
        robots_labelled = draw_microrobots(robots_labelled, robots, False)

        if grayscale:
            plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_microrobots_labelled.png'),
                       robots_labelled, cmap='gray')
            plt.imsave(pathlib.Path(root_directory, f'{filename}_microrobots_labelled.png'),
                       robots_labelled, cmap='gray')
            # plt.imshow(robots_labelled, cmap='gray')
            # plt.show()
        else:
            plt.imsave(pathlib.Path(output_directory, f'{filename}_{out_num}_microrobots_labelled.png'),
                       robots_labelled)
            plt.imsave(pathlib.Path(root_directory, f'{filename}_microrobots_labelled.png'),
                       robots_labelled)
            # plt.imshow(robots_labelled)
            # plt.show()

        output_microrobots(robots, filename, output_directory)

    return robots, robots_mask


def detect_microrobots(image, method, filename=None, output_directory=None, root_directory=None, output_results=False):
    if method == 'intensity':
        robots, robots_mask = detect_microrobots_intensity(image, filename, output_directory, root_directory,
                                                           output_results)

    elif method == 'edges':
        robots, robots_mask = detect_microrobots_edges(image, filename, output_directory, root_directory,
                                                       output_results)

    else:
        print('Error: Method parameter must either be "intensity" or "edges".', file=sys.stderr)
        sys.exit(1)

    if output_results:
        output_microrobots(robots, filename, root_directory)

    return robots, robots_mask


def main():
    # ---------- Parameters ----------

    output_results = True
    process_only = -1

    # Detection method of the microrobots
    # 'intensity': Suitable for clumped and uniform/clean/light robots
    # 'edges': Suitable for isolated and non-uniform/dirty/dark robots
    detection_method = 'intensity'

    if detection_method != 'intensity' and detection_method != 'edges':
        print('Error: Microrobots detection method must either be "intensity" or "edges".', file=sys.stderr)
        sys.exit(1)

    # ---------- File IO ----------

    # in_path = '/media/lo/DATA SSD/UCL/Research/Microrobots_detection/2020-9-22 microrobot for Chris/20200922/5x/'
    # in_path = '/media/lo/DATA SSD/UCL/Research/Microrobots_detection/Microrobots/'
    # out_path = '/media/lo/DATA SSD/UCL/Research/Microrobots_detection/Results/'

    # in_path = pathlib.Path('E:', 'UCL', 'Research', 'Microrobots_detection', 'Microrobots_ucl')
    in_path = pathlib.Path('L:', 'moving robots', 'test')
    out_path = pathlib.Path('L:', 'moving robots', 'test_results')
    # out_path = pathlib.Path('E:', 'UCL', 'Research', 'Microrobots_detection', 'Results')
    all_out_path = pathlib.Path(out_path, 'All_outputs')

    if not pathlib.Path.exists(out_path):
        pathlib.Path.mkdir(out_path)

    if not pathlib.Path.exists(all_out_path):
        pathlib.Path.mkdir(all_out_path)

    files = []

    for file in pathlib.Path(in_path).rglob('*.png'):
        files.append(file)

    num_files = len(files)
    num_files_processed = 0

    start_time = time.time()

    for file in files:
        num_files_processed += 1

        if num_files_processed < process_only:
            continue

        filename_ext = file.name
        filename_cut = file.stem

        print(f'Processing file: {filename_ext} ({num_files_processed}/{num_files})')

        # ---------- Image IO ----------

        image = io.imread(pathlib.Path(in_path, filename_ext).__str__())

        # ---------- Microrobots detection ----------

        detect_microrobots(image, detection_method, filename_cut, all_out_path, out_path, output_results)

        if num_files_processed == process_only:
            break

    # ---------- Time processing ----------

    end_time = time.time()
    total_time = end_time - start_time

    total_time_txt = f'Time to process {num_files_processed} images: {total_time:.2f}(s)\n' \
                     f'Average time per image: {total_time / num_files_processed:.2f}(s)'

    print(total_time_txt)

    f = open(pathlib.Path(out_path, 'time.txt'), 'w')
    f.write(total_time_txt)
    f.close()

    sys.exit(0)


if __name__ == '__main__':
    main()
