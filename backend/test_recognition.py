import requests

url = "http://127.0.0.1:5000/api/recognize"

with open("../known_faces/John/john.png", "rb") as f:
    response = requests.post(url, files={"image": f})

print(response.json())