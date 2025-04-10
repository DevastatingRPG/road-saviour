import os
import io
import socket
import time

from image_processing import signal_detection

from typing import Union
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Response
from fastapi import FastAPI

app = FastAPI()
esp32_ip = ""  # Change this to the IP address of your ESP32
esp32_port = 8002

# Global socket object
esp32_socket = None

# Global variable to store the received data
received_data = None

# Violations
violations = {"traffic": 0, "zebra": 0}

# Function to establish a socket connection
def connect_to_esp32():
    global esp32_socket
    while True:
        try:
            esp32_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            esp32_socket.connect((esp32_ip, esp32_port))
            print("Connected to ESP32 successfully.")
            break
        except Exception as e:
            print(f"Failed to connect to ESP32: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# Establish connection at startup
@app.on_event("startup")
def startup_event():
    connect_to_esp32()

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Receive image from ESP32 and save it to a file
@app.post("/upload-image/")
def upload_image(file: bytes):
    with open("received_image.jpg", "wb") as f:
        f.write(file)
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
    return result

'''
Signals the start of violation by ESP32 Bot
1. Input: 1 or 2 (1 for signal violation, 2 for zebra crossing violation)
2. Save the violation type to a global variable violations
'''
@app.post("/violation-start/")
def violation_start(violation_type: int):
    global violations
    if violation_type == 1:
        violations["traffic"] = 1
    elif violation_type == 2:
        violations["zebra"] = 1 
    else:
        return {"status": "error", "message": "Invalid violation type"}
    
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
    
    return {"status": "success", "violations": violations}


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
        esp32_socket.sendall(command.encode())
        return {"status": "success", "command": command}
    except Exception as e:
        return {"status": "error", "message": str(e)}

