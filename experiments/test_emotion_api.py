# backend/test_emotion_api.py
import base64
import requests

# Step 1: Load image
with open("lena.jpg", "rb") as image_file:
    encoded = base64.b64encode(image_file.read()).decode("utf-8")

# Step 2: Prepare JSON payload
payload = {"image": f"data:image/jpeg;base64,{encoded}"}

# Step 3: Send POST request
response = requests.post("http://127.0.0.1:8000/api/emotion_face/frame", json=payload)

# Step 4: Print result
print("Status:", response.status_code)
print("Response:", response.json())
