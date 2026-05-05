import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 100, "offset": offset}
    return requests.get(url, params=params).json()

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, data=data)

def main():
    offset = None

    while True:
        updates = get_updates(offset)

        for update in updates["result"]:
            offset = update["update_id"] + 1

            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "")

                # Echo response
                send_message(chat_id, f"Was ist deine Problem?")

        time.sleep(1)

if __name__ == "__main__":
    main()