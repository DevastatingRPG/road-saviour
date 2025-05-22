import os
import time
import requests
import random

# Configuration
BASE_URL = "http://localhost:8000"  # Update if your FastAPI server runs elsewhere
DATASET_FOLDER = "../dataset"  # Folder containing images to simulate
ESP32_NAME = "ESP32_Cam_01"
VIOLATION_TYPE = 1  # 1 for signal violation
LOCATION = "Salunke Vihar"

def register_name():
    response = requests.post(f"{BASE_URL}/register-name/", params={"name": ESP32_NAME})
    print("Register name:", response.json())

def start_violation():
    response = requests.post(f"{BASE_URL}/violation-start/", params={
        "violation_type": VIOLATION_TYPE,
        "location": LOCATION
    })
    print("Violation start:", response.json())

def send_images_for_duration(duration_sec=10):
    image_files = [f for f in os.listdir(DATASET_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    start_time = time.time()

    while time.time() - start_time < duration_sec:
        if not image_files:
            break
        image_path = os.path.join(DATASET_FOLDER, random.choice(image_files))
        with open(image_path, "rb") as img:
            response = requests.post(f"{BASE_URL}/upload-image/", files={"file": img})
            print(f"Uploaded {os.path.basename(image_path)}: {response.status_code}")
        time.sleep(1)  # Send 1 image per second

def end_violation():
    response = requests.post(f"{BASE_URL}/violation-end/", params={"violation_type": VIOLATION_TYPE})
    print("Violation end:", response.json())

if __name__ == "__main__":
    register_name()
    start_violation()
    send_images_for_duration(10)
    end_violation()
    # import cv2
    # frame = cv2.imread("violation_frames\frame_0000.jpg")
    # print(frame)