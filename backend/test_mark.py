import requests

url = "http://127.0.0.1:5000/mark_attendance"

# Ask for a name in console
name = input("Enter name to mark attendance: ").strip()

if name == "":
    print("Name cannot be empty!")
else:
    response = requests.post(url, json={"name": name})
    print("Response:", response.json())