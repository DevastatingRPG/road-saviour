import os
import io
import socket
import datetime
import time
import cv2

from image_processing import signal_detection

from typing import Union
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Response
from fastapi import FastAPI

import threading

# Global variable to track connection status
esp32_connected = False

app = FastAPI()
# esp32_ip = "192.168.1.26"  # Change this to the IP address of your ESP32
esp32_ip = ""
esp32_port = 8002

# Global socket object
esp32_socket = None
esp32_conn = None

# Global variable to store the name and location
esp32_name = None
esp32_location = None

# Global variable to store the received data
received_data = None

# Violations
violations = {"traffic": 0, "zebra": 0}
violation_timestamp = None

# Directory to save frames
frames_dir = "violation_frames"
os.makedirs(frames_dir, exist_ok=True)

# Frame counter
frame_counter = 0

# Function to establish a socket connection
def connect_to_esp32():
    global esp32_socket, esp32_conn
    while True:
        try:
            esp32_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            esp32_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            esp32_socket.bind((esp32_ip, esp32_port))
            esp32_socket.listen()
            esp32_conn, addr = esp32_socket.accept()
            esp32_connected = True
            # esp32_socket.connect((esp32_ip, esp32_port))
            print("Connected to ESP32 successfully.")
            
            # Receive the name from ESP32
            data = esp32_conn.recv(1024).decode().strip()
            if data.startswith("NAME:"):
                esp32_name = data.split(":", 1)[1]
                print(f"Received name from ESP32: {esp32_name}")
            else:
                print(f"Unexpected message from ESP32 during connection: {data}")
            break
        except Exception as e:
            print(f"Failed to connect to ESP32: {e}. Retrying in 5 seconds...")
            time.sleep(5)


# Function to send a heartbeat message to ESP32
def heartbeat():
    global esp32_conn, esp32_connected
    while True:
        if esp32_connected:
            try:
                # Send the heartbeat command (command number 9)
                esp32_conn.sendall(b"9")
                # Wait for a response
                response = esp32_conn.recv(1024)
                if response.decode().strip() != "ACK":
                    raise Exception("Invalid response from ESP32")
            except Exception as e:
                print(f"Heartbeat failed: {e}. Reconnecting...")
                esp32_connected = False
                connect_to_esp32()
        time.sleep(5)  # Send heartbeat every 5 seconds


# Establish connection at startup
@app.on_event("startup")
def startup_event():
    # connect_to_esp32()
    threading.Thread(target=connect_to_esp32, daemon=True).start()
    threading.Thread(target=heartbeat, daemon=True).start()


@app.get("/")
def read_root():
    return {"Hello": "World"}

# Receive image from ESP32 and save it to a file
@app.post("/upload-image/")
def upload_image(file: bytes):
    with open("received_image.jpg", "wb") as f:
        f.write(file)
    # If a violation is ongoing, save the frame
    if violations["traffic"] == 1 or violations["zebra"] == 1:
        frame_path = os.path.join(frames_dir, f"frame_{frame_counter:04d}.jpg")
        with open(frame_path, "wb") as f:
            f.write(file)
        frame_counter += 1

    return {"filename": "received_image.jpg"}


# Send received file to web browser
@app.get("/get-image/")
def get_image():
    with open("received_image.jpg", "rb") as f:
        image_data = f.read()
    return JSONResponse(
        content={
            "image": StreamingResponse(io.BytesIO(image_data), media_type="image/jpeg"),
            "violations": violations,
        }
    )

'''
Receive image from ESP32:
1. Save image to a file
2. Return signal and zebra crossing detection result to ESP32
'''
@app.post("/process-image/")
async def process_image(file: bytes):
    with open("received_image.jpg", "wb") as f:
        f.write(file)
    # Process the image and return the result
    # For example, you can use OpenCV to detect objects in the image
    # Here we just return a dummy result
    signal_detected = signal_detection("received_image.jpg")
    zebra_crossing_detected = False  # Replace with actual detection logic
    result = {"signal": signal_detected, "zebra_crossing_detected": zebra_crossing_detected}
        # If a violation is ongoing, save the frame
    if violations["traffic"] == 1 or violations["zebra"] == 1:
        frame_path = os.path.join(frames_dir, f"frame_{frame_counter:04d}.jpg")
        with open(frame_path, "wb") as f:
            f.write(file)
        frame_counter += 1

    return result

'''
Signals the start of violation by ESP32 Bot
1. Input: 1 or 2 (1 for signal violation, 2 for zebra crossing violation)
2. Save the violation type to a global variable violations
'''
@app.post("/violation-start/")
def violation_start(violation_type: int, location: str):
    global violations, frame_counter, esp32_location, violation_timestamp

    # Store the location
    esp32_location = location
    print(f"Violation started at location: {esp32_location}")

    if violation_type == 1:
        violations["traffic"] = 1
    elif violation_type == 2:
        violations["zebra"] = 1 
    else:
        return {"status": "error", "message": "Invalid violation type"}
    

    # Reset the frame counter and clear previous frames
    violation_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    frame_counter = 0

    for file in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, file))

    return {"status": "success", "violations": violations}


''' 
Signals the end of violation by ESP32 Bot
1. Input: 1 or 2 (1 for signal violation, 2 for zebra crossing violation)
2. Reset the violation type in the global variable violations
'''
@app.post("/violation-end/")
def violation_end(violation_type: int):
    global violations

    if violation_type == 1:
        violations["traffic"] = 0
    elif violation_type == 2:
        violations["zebra"] = 0
    else:
        return {"status": "error", "message": "Invalid violation type"}

    # Ensure violation_timestamp and esp32_name are set
    if not violation_timestamp or not esp32_name:
        return {"status": "error", "message": "Violation timestamp or ESP32 name is missing"}

    # Create a unique filename using violation_timestamp and esp32_name
    sanitized_timestamp = violation_timestamp.replace(":", "-").replace(" ", "_")  # Sanitize timestamp for filename
    video_filename = f"{esp32_name}_{sanitized_timestamp}.mp4"
    video_dir = "video_evidence"
    os.makedirs(video_dir, exist_ok=True)
    video_filepath = os.path.join(video_dir, video_filename)

    # Get all frame file paths
    frame_files = sorted(
        [os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.endswith(".jpg")]
    )

    if frame_files:
        # Get the frame size from the first frame
        frame = cv2.imread(frame_files[0])
        height, width, _ = frame.shape

        # Create a video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(video_filepath, fourcc, 10, (width, height))

        # Write each frame to the video
        for frame_file in frame_files:
            frame = cv2.imread(frame_file)
            video_writer.write(frame)

        video_writer.release()
    
    # Save name, location, timestamp, and video filename to a CSV file
    csv_file = "video_evidence.csv"
    with open(csv_file, "a") as f:
        f.write(f"{esp32_name},{esp32_location},{violation_timestamp},{video_filename}\n")


    return {"status": "success", "video": video_filename}


'''
Receieve video evidence of violation from ESP32, along with timestamp, name and location
1. Generate a unique filename for the video 
2. Save video to a file
3. Save name, location, timestamp and video file name to a csv file (existing file)
4. Return success code
'''
@app.post("/upload-video/")
def upload_video(file: bytes, name: str, location: str, timestamp: str):
    # Generate a unique filename for the video
    filename = f"{name}_{timestamp}.mp4"
    video_dir = "video_evidence"
    # Create the directory if it doesn't exist
    if not os.path.exists(video_dir):
        os.makedirs(video_dir)
    
    filepath = os.path.join(video_dir, filename)
    with open(filepath, "wb") as f:
        f.write(file)
    
    # Save name, location, timestamp and video file name to a csv file
    with open("video_evidence.csv", "a") as f:
        f.write(f"{name},{location},{timestamp},{filename}\n")
    
    return {"filename": filename, "status": "success"}


'''
Receive a command from the web browser to actuate the ESP32 Bot
1. Parse the command from the request
2. Send the command to the ESP32 Bot via WiFi communication
'''
@app.post("/send-command/")
def send_command(command: str):
    global esp32_socket
    try:
        # Send the command to the ESP32
        esp32_conn.sendall(command.encode())
        return {"status": "success", "command": command}
    except Exception as e:
        return {"status": "error", "message": str(e)}

