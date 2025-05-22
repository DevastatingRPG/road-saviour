import requests

# URL of the endpoint
url = "http://localhost:8000/process-image/"

# Path to the image file
image_path = "combined.png"

# Read the image file in binary mode
with open(image_path, "rb") as file:
    image_data = file.read()

# Send the POST request
response = requests.post(url, data=image_data)

# Print the response
print("Status Code:", response.status_code)
print("Response JSON:", response.json())