import os
import requests

WEBHOOK_URL = os.environ["GUIDES_WEBHOOK_URL"]

IMAGE_URL = "https://raw.githubusercontent.com/Shaynah87/aion2-discord/main/Guides/coming_soon_g.png"

payload = {
    "username": "Nyerk24 · Guides",
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
    print("Guides wurde erfolgreich gepostet.")
else:
    print("Fehler:", response.status_code)
    print(response.text)
