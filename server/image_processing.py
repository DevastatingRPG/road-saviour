import cv2
import numpy as np
from PIL import Image
from io import BytesIO

import cv2
import numpy as np

def signal_detection(image_path="received_image.jpg"):
    '''
    1. Read image from received_image.jpg file
    2. Convert image to HSV color space
    3. Extract the Value (V) channel and apply a threshold
    4. Use the thresholded V channel as a mask
    5. Define color ranges for red, green, and yellow signals
    6. Create binary masks for red, green, and yellow signals using the defined color ranges
    7. Combine the threshold mask with the individual color masks
    8. Find number of pixels in each mask
    9. Check which mask has the highest number of pixels and is above 50
    10. Return the signal color if detected, otherwise return "unknown"
    '''
    # Read image from received_image.jpg file
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found at {image_path}")

    # Convert image to HSV color space
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

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

    # Create binary masks for red, green, and yellow signals using the defined color ranges
    red_mask1 = cv2.inRange(hsv_masked, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv_masked, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    yellow_mask = cv2.inRange(hsv_masked, yellow_lower, yellow_upper)
    green_mask = cv2.inRange(hsv_masked, green_lower, green_upper)

    # Count the number of pixels in each mask
    red_pixels = cv2.countNonZero(red_mask)
    # yellow_pixels = cv2.countNonZero(yellow_mask)
    yellow_pixels = 0  # Placeholder for yellow pixels count
    green_pixels = cv2.countNonZero(green_mask)

    # Determine the dominant color
    if red_pixels > 1 and red_pixels > yellow_pixels and red_pixels > green_pixels:
        return "red"
    elif green_pixels > 1 and green_pixels > red_pixels and green_pixels > yellow_pixels:
        return "green"
    # elif yellow_pixels > 1 and yellow_pixels > red_pixels and yellow_pixels > green_pixels:
    #     return "yellow"
    else:
        return "unknown"

def zebra_detection(image_path="received_image.jpg"):
    '''
    1. Read image from received_image.jpg file
    2. Convert image to grayscale
    3. Apply Gaussian blur to the image
    4. Use Canny edge detection to find edges in the image
    5. Perform Morphological opening to remove small noise
    5. Find contours in the edge-detected image
    6. Filter contours based on area and aspect ratio to identify zebra crossings
    7. Draw bounding boxes around detected zebra crossings
    8. Return True if a zebra crossing is detected, otherwise return False
    '''
    # Read image from received_image.jpg file
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found at {image_path}")

    # Convert image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to the image
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Use Canny edge detection to find edges in the image
    edges = cv2.Canny(blurred, 50, 150)

    # Define a kernel for morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    # Perform morphological opening to remove small noise
    opened_edges = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel)

    # Find contours in the cleaned-up edge-detected image
    contours, _ = cv2.findContours(opened_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area and aspect ratio to identify zebra crossings
    detected_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 100:  # Adjust this threshold as needed
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h

            # Check for a rectangular shape (aspect ratio close to 1)
            if aspect_ratio > 0.5 and aspect_ratio < 1.5:
                # return True
                detected_contours.append(contour)

    return detected_contours