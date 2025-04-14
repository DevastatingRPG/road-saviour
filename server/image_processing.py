import cv2
import numpy as np
from PIL import Image
import math
from itertools import combinations
from sklearn.linear_model import LinearRegression

from io import BytesIO

import cv2
import numpy as np

# def signal_detection(image_path="received_image.jpg"):
#     '''
#     1. Read image from received_image.jpg file
#     2. Convert image to HSV color space
#     3. Extract the Value (V) channel and apply a threshold
#     4. Use the thresholded V channel as a mask
#     5. Define color ranges for red, green, and yellow signals
#     6. Create binary masks for red, green, and yellow signals using the defined color ranges
#     7. Combine the threshold mask with the individual color masks
#     8. Find number of pixels in each mask
#     9. Check which mask has the highest number of pixels and is above 50
#     10. Return the signal color if detected, otherwise return "unknown"
#     '''
#     # Read image from received_image.jpg file
#     image = cv2.imread(image_path)
#     if image is None:
#         raise FileNotFoundError(f"Image not found at {image_path}")

#     # Convert image to HSV color space
#     hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

#     # Extract the Value (V) channel
#     _, _, v = cv2.split(hsv)

#     # Apply a threshold to the V channel
#     _, thresholded_v = cv2.threshold(v, 180, 255, cv2.THRESH_BINARY)

#     # Use the thresholded V channel as a mask
#     masked_image = cv2.bitwise_and(image, image, mask=thresholded_v)

#     # Convert the masked image to HSV
#     hsv_masked = cv2.cvtColor(masked_image, cv2.COLOR_BGR2HSV)

#     # Define color ranges for red, green, and yellow signals
#     red_lower1 = (0, 50, 50)
#     red_upper1 = (10, 255, 255)
#     red_lower2 = (170, 50, 50)
#     red_upper2 = (180, 255, 255)
#     yellow_lower = (20, 50, 50)
#     yellow_upper = (30, 255, 255)
#     green_lower = (40, 50, 50)
#     green_upper = (80, 255, 255)

#     # Create binary masks for red, green, and yellow signals using the defined color ranges
#     red_mask1 = cv2.inRange(hsv_masked, red_lower1, red_upper1)
#     red_mask2 = cv2.inRange(hsv_masked, red_lower2, red_upper2)
#     red_mask = cv2.bitwise_or(red_mask1, red_mask2)
#     yellow_mask = cv2.inRange(hsv_masked, yellow_lower, yellow_upper)
#     green_mask = cv2.inRange(hsv_masked, green_lower, green_upper)

#     # Count the number of pixels in each mask
#     red_pixels = cv2.countNonZero(red_mask)
#     # yellow_pixels = cv2.countNonZero(yellow_mask)
#     yellow_pixels = 0  # Placeholder for yellow pixels count
#     green_pixels = cv2.countNonZero(green_mask)

#     # Determine the dominant color
#     if red_pixels > 1 and red_pixels > yellow_pixels and red_pixels > green_pixels:
#         return "red"
#     elif green_pixels > 1 and green_pixels > red_pixels and green_pixels > yellow_pixels:
#         return "green"
#     # elif yellow_pixels > 1 and yellow_pixels > red_pixels and yellow_pixels > green_pixels:
#     #     return "yellow"
#     else:
#         return "unknown"

def filter_contours_by_pixel_count(contours, mask, pixel_threshold):
    """
    Filters contours based on the number of non-zero pixels inside them.

    Args:
        contours (list): List of contours to filter.
        mask (numpy.ndarray): Binary mask of the image.
        pixel_threshold (int): Minimum number of pixels required for a contour to be valid.

    Returns:
        list: Filtered contours that meet the pixel threshold.
    """
    valid_contours = []
    for contour in contours:
        # Create a mask for the current contour
        contour_mask = np.zeros_like(mask)
        cv2.drawContours(contour_mask, [contour], -1, 255, thickness=cv2.FILLED)

        # Count the number of non-zero pixels inside the contour
        pixel_count = cv2.countNonZero(cv2.bitwise_and(mask, contour_mask))

        # Check if the pixel count meets the threshold
        if pixel_count >= pixel_threshold:
            valid_contours.append(contour)

    return valid_contours


def signal_detection(image_path="received_image.jpg"):
    '''
    1. Read image from received_image.jpg file
    2. Convert image to HSV color space
    3. Define color ranges for red, green, and yellow signals
    4. Create binary masks for red, green, and yellow signals
    5. Find contours for each mask
    6. Filter signals based on the highest bounding box (smallest y-coordinate)
    7. Return the signal color if detected, otherwise return "unknown"
    '''
    pixel_threshold = 15  # Minimum number of pixels required for a contour to be valid
    # Read image from received_image.jpg file
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found at {image_path}")

    # Get the height and width of the image
    height, width = image.shape[:2]

    # Mask the lower half of the image by making it black
    mask = np.zeros_like(image)
    mask[:height // 2, :] = image[:height // 2, :]  # Keep only the upper half
    masked_image = mask

    # Convert image to HSV color space
    hsv = cv2.cvtColor(masked_image, cv2.COLOR_BGR2HSV)

    # Extract the Value (V) channel
    _, _, v = cv2.split(hsv)

    # Apply a threshold to the V channel
    _, thresholded_v = cv2.threshold(v, 180, 255, cv2.THRESH_BINARY)

    # Use the thresholded V channel as a mask
    masked_image = cv2.bitwise_and(image, image, mask=thresholded_v)

    # Convert the masked image to HSV
    hsv_masked = cv2.cvtColor(masked_image, cv2.COLOR_BGR2HSV)

    # Define color ranges for red, green, and yellow signals
    red_lower1 = (0, 50, 50)
    red_upper1 = (10, 255, 255)
    red_lower2 = (170, 50, 50)
    red_upper2 = (180, 255, 255)
    yellow_lower = (20, 50, 50)
    yellow_upper = (30, 255, 255)
    green_lower = (40, 50, 50)
    green_upper = (80, 255, 255)

    # Create binary masks for red, green, and yellow signals
    red_mask1 = cv2.inRange(hsv_masked, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv_masked, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    yellow_mask = cv2.inRange(hsv_masked, yellow_lower, yellow_upper)
    green_mask = cv2.inRange(hsv_masked, green_lower, green_upper)

    # Helper function to find the highest valid group based on connected components
    def find_highest_valid_group(mask, pixel_threshold):
        # Perform connected component analysis
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

        highest_y = float('inf')
        highest_label = None

        for label in range(1, num_labels):  # Skip the background label (0)
            pixel_count = stats[label, cv2.CC_STAT_AREA]
            y = stats[label, cv2.CC_STAT_TOP]

            # Check if the group meets the pixel threshold and is the highest
            if pixel_count >= pixel_threshold and y < highest_y:
                highest_y = y
                highest_label = label

        return highest_label, labels, stats

    # Find the highest valid group for each signal
    highest_red_label, red_labels, red_stats = find_highest_valid_group(red_mask, pixel_threshold)
    highest_yellow_label, yellow_labels, yellow_stats = find_highest_valid_group(yellow_mask, pixel_threshold)
    highest_green_label, green_labels, green_stats = find_highest_valid_group(green_mask, pixel_threshold)

    # Determine the dominant signal based on the highest group
    signals = []
    if highest_red_label is not None:
        signals.append(("red", highest_red_label, red_stats))
    # if highest_yellow_label is not None:
    #     signals.append(("yellow", highest_yellow_label, yellow_stats))
    if highest_green_label is not None:
        signals.append(("green", highest_green_label, green_stats))


    # Sort signals by the y-coordinate of their highest group (ascending order)
    signals.sort(key=lambda s: s[2][s[1], cv2.CC_STAT_TOP])


    # Return the color of the signal that is highest in the image
    if signals:
        return signals[0][0]
    else:
        return "unknown"



def zebra_detection(image_path="received_image.jpg"):
    '''
    1. Read image from received_image.jpg file
    2. Add zero padding (black border) of width 5
    3. Mask the upper two-thirds of the image by making it black
    4. Convert the masked image to grayscale
    5. Apply histogram equalization to enhance contrast
    6. Apply Gaussian blur to the masked image
    7. Use Canny edge detection to find edges in the masked image
    8. Find contours in the edge-detected masked image
    9. Adjust contours back to fit the original image dimensions
    10. Filter contours based on area, aspect ratio (using rotated bounding rectangle), and number of corners
    11. Return filtered contours
    '''
    # Read image from received_image.jpg file
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found at {image_path}")

    # Add zero padding (black border) of width 5
    padding = 5
    padded_image = cv2.copyMakeBorder(image, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=(0, 0, 0))

    # Get the height and width of the padded image
    height, width = padded_image.shape[:2]

    # Mask the upper two-thirds of the image by making it black
    mask = np.zeros_like(padded_image)
    mask[int(height * 2 / 3):, :] = padded_image[int(height * 2 / 3):, :]
    masked_image = mask

    # Convert the masked image to grayscale
    gray = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)
    
    # Apply histogram equalization to enhance contrast
    equalized = cv2.equalizeHist(gray)
    
    # Apply Gaussian blur to the masked image
    blurred = cv2.GaussianBlur(equalized, (5, 5), 0)

    # Define a kernel for morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    # Perform morphological opening to remove small noise
    opened = cv2.morphologyEx(blurred, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

    # Apply binary thresholding
    _, thresholded = cv2.threshold(closed, 150, 255, cv2.THRESH_BINARY)

    # Use Canny edge detection to find edges in the masked image
    edges = cv2.Canny(thresholded, 50, 150)

    # Find contours in the edge-detected masked image
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Adjust contours back to fit the original image dimensions
    adjusted_contours = []
    for contour in contours:
        adjusted_contour = contour - np.array([padding, padding])  # Subtract padding
        adjusted_contours.append(adjusted_contour)

    # Filter contours based on area, aspect ratio (rotated bounding rectangle), and number of corners
    filtered_contours = []
    centers = []
    for contour in adjusted_contours:
        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(contour, True)  # Adjust epsilon as needed
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check the number of corners
        num_corners = len(approx)
        if 3 <= num_corners <= 5:  # Only consider contours with 3 to 5 corners
            area = cv2.contourArea(contour)
            if area > 20:  # Adjust this threshold as needed
                # Get the rotated bounding rectangle
                rect = cv2.minAreaRect(contour)
                width, height = rect[1]  # rect[1] contains (width, height)

                # Avoid division by zero
                if width == 0 or height == 0:
                    continue

                # Calculate the aspect ratio of the rotated bounding rectangle
                aspect_ratio = max(width, height) / min(width, height)

                # Check for a rectangular shape (aspect ratio close to 1)
                if 0.5 <= aspect_ratio <= 5:
                    filtered_contours.append(approx)

                    # Calculate the center of the contour
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        centers.append((cx, cy))

    # Check if a straight line can be formed through at least 3 centers
    zebra_detected = False
    specific_contours = []
    if len(centers) >= 3:
        # Iterate through all combinations of 3 points
        for comb in combinations(range(len(centers)), 3):
            p1, p2, p3 = centers[comb[0]], centers[comb[1]], centers[comb[2]]

            # Sort points by x-coordinate (leftmost, center, rightmost)
            sorted_points = sorted([p1, p2, p3], key=lambda x: x[0])
            left, center, right = sorted_points

            # Calculate angles of the two lines with the horizontal axis
            angle1 = math.degrees(math.atan2(center[1] - left[1], center[0] - left[0]))
            angle2 = math.degrees(math.atan2(right[1] - center[1], right[0] - center[0]))

            # Check if the angles are within a threshold
            angle_diff = abs(angle1 - angle2)
            if angle_diff < 10:  # Adjust this threshold as needed
                zebra_detected = True
                specific_contours = [filtered_contours[comb[0]], filtered_contours[comb[1]], filtered_contours[comb[2]]]
                break

    return zebra_detected

                    

# def zebra_detection(image_path="received_image.jpg"):
#     '''
#     1. Read image from received_image.jpg file
#     2. Add zero padding (black border) of width 5
#     3. Mask the upper two-thirds of the image by making it black
#     4. Convert the masked image to grayscale
#     5. Apply histogram equalization to enhance contrast
#     6. Apply Gaussian blur to the masked image
#     7. Use Canny edge detection to find edges in the masked image
#     8. Find contours in the edge-detected masked image
#     9. Adjust contours back to fit the original image dimensions
#     10. Filter contours based on area, aspect ratio (using rotated bounding rectangle), and number of corners
#     11. Return filtered contours
#     '''
#     # Read image from received_image.jpg file
#     image = cv2.imread(image_path)
#     if image is None:
#         raise FileNotFoundError(f"Image not found at {image_path}")

#     # Add zero padding (black border) of width 5
#     padding = 5
#     padded_image = cv2.copyMakeBorder(image, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=(0, 0, 0))

#     # Get the height and width of the padded image
#     height, width = padded_image.shape[:2]

#     # Mask the upper two-thirds of the image by making it black
#     mask = np.zeros_like(padded_image)
#     mask[int(height * 2 / 3):, :] = padded_image[int(height * 2 / 3):, :]
#     masked_image = mask

#     # Convert the masked image to grayscale
#     gray = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)
    
#     # Apply histogram equalization to enhance contrast
#     equalized = cv2.equalizeHist(gray)
    
#     # Apply Gaussian blur to the masked image
#     blurred = cv2.GaussianBlur(equalized, (5, 5), 0)

#     # Define a kernel for morphological operations
#     kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

#     # Perform morphological opening to remove small noise
#     opened = cv2.morphologyEx(blurred, cv2.MORPH_OPEN, kernel)
#     closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

#     # Apply binary thresholding
#     _, thresholded = cv2.threshold(closed, 150, 255, cv2.THRESH_BINARY)

#     # Use Canny edge detection to find edges in the masked image
#     edges = cv2.Canny(thresholded, 50, 150)

#     # Find contours in the edge-detected masked image
#     contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

#     # Adjust contours back to fit the original image dimensions
#     adjusted_contours = []
#     for contour in contours:
#         adjusted_contour = contour - np.array([padding, padding])  # Subtract padding
#         adjusted_contours.append(adjusted_contour)

#     # Filter contours based on area, aspect ratio (rotated bounding rectangle), and number of corners
#     filtered_contours = []
#     centers = []
#     for contour in adjusted_contours:
#         # Approximate the contour to a polygon
#         epsilon = 0.02 * cv2.arcLength(contour, True)  # Adjust epsilon as needed
#         approx = cv2.approxPolyDP(contour, epsilon, True)

#         # Check the number of corners
#         num_corners = len(approx)
#         if 3 <= num_corners <= 5:  # Only consider contours with 3 to 5 corners
#             area = cv2.contourArea(contour)
#             if area > 20:  # Adjust this threshold as needed
#                 # Get the rotated bounding rectangle
#                 rect = cv2.minAreaRect(contour)
#                 width, height = rect[1]  # rect[1] contains (width, height)

#                 # Avoid division by zero
#                 if width == 0 or height == 0:
#                     continue

#                 # Calculate the aspect ratio of the rotated bounding rectangle
#                 aspect_ratio = max(width, height) / min(width, height)

#                 # Check for a rectangular shape (aspect ratio close to 1)
#                 if 0.5 <= aspect_ratio <= 5:
#                     filtered_contours.append(approx)

#                     # Calculate the center of the contour
#                     M = cv2.moments(contour)
#                     if M["m00"] != 0:
#                         cx = int(M["m10"] / M["m00"])
#                         cy = int(M["m01"] / M["m00"])
#                         centers.append((cx, cy))

# # Identify horizontal edges
#     horizontal_edges = []
#     centers = []
#     angle_threshold = 45  # Angle threshold for horizontal edges (in degrees)
#     for contour in filtered_contours:
#         rect = cv2.minAreaRect(contour)
#         box = cv2.boxPoints(rect)
#         box = np.int0(box)

#         # Calculate the angle of the edge
#         edge_angle = abs(rect[2])  # Angle of the rotated rectangle
#         if edge_angle > 45:
#             edge_angle = 90 - edge_angle  # Normalize angle to [0, 45]

#         if edge_angle <= angle_threshold:  # Check if the edge is nearly horizontal
#             horizontal_edges.append(box)

#             # Calculate the center of the edge
#             cx = int((box[0][0] + box[2][0]) / 2)
#             cy = int((box[0][1] + box[2][1]) / 2)
#             centers.append((cx, cy))

#     # Check for triplets of horizontal edges
#     zebra_detected = False
#     for triplet in combinations(range(len(horizontal_edges)), 3):
#         p1, p2, p3 = centers[triplet[0]], centers[triplet[1]], centers[triplet[2]]

#         # Calculate slopes between the centers
#         slope1 = (p2[1] - p1[1]) / (p2[0] - p1[0] + 1e-6)  # Avoid division by zero
#         slope2 = (p3[1] - p2[1]) / (p3[0] - p2[0] + 1e-6)

#         # Check if slopes are similar
#         if abs(slope1 - slope2) < 0.1:  # Adjust slope similarity threshold as needed
#             # Check if the centers are roughly aligned
#             line_angle = math.degrees(math.atan2(p3[1] - p1[1], p3[0] - p1[0]))
#             if abs(line_angle) < angle_threshold:  # Check if the line is nearly horizontal
#                 zebra_detected = True
#                 break

#     return zebra_detected, filtered_contours, horizontal_edges



