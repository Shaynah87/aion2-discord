import os
import requests

WEBHOOK_URL = os.environ["UPDATES_WEBHOOK_URL"]

IMAGE_URL = "https://raw.githubusercontent.com/Shaynah87/aion2-discord/main/Updates/coming_soon_n.png"

payload = {
    "username": "Nyerk24 · News",
    "embeds": [
        {
            "image": {
                "url": IMAGE_URL
            }
        }
    ]
}

response = requests.post(WEBHOOK_URL, json=payload)

if response.status_code in (200, 204):
    print("Updates wurde erfolgreich gepostet.")
else:
    print("Fehler:", response.status_code)
    print(response.text)
