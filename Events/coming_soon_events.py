import requests

WEBHOOK_URL = https://discord.com/api/webhooks/1545723322224877608/5GWa3NYYfkxrAOoJQOtg9PaXMWK7n0kcWnGrAzs0u7qDo1IcslpQoqI9uDKfjoz-fQLC

IMAGE_URL = "https://raw.githubusercontent.com/Shaynah87/aion2-discord/main/Events/coming_soon_e.png"

payload = {
    "username": "Nyerk24 · Events",
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
    print("Coming Soon · Events wurde erfolgreich gepostet.")
else:
    print("Fehler:", response.status_code)
    print(response.text)
