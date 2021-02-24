import json
from collections import defaultdict
from pathlib import Path
from typing import Dict

import httpx
import lxml.html


STORE_URL = {
    "NA": {
        "App Store": "http://itunes.apple.com/lookup?bundleId=com.aniplex.fategrandorder.en&country=us",
        "Play Store": "https://play.google.com/store/apps/details?id=com.aniplex.fategrandorder.en",
    },
    "JP": {
        "App Store": "http://itunes.apple.com/lookup?bundleId=com.aniplex.fategrandorder&country=jp",
        "Play Store": "https://play.google.com/store/apps/details?id=com.aniplex.fategrandorder",
    },
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"
PLAY_STORE_XPATH = "/html/body/div[1]/div[4]/c-wiz/div/div[2]/div/div/main/c-wiz[4]/div[1]/div[2]/div/div[4]/span/div/span"
HEADERS = {"user-agent": USER_AGENT}


with open("WEBHOOK.url", encoding="utf-8") as webhook_fp:
    WEBHOOK = webhook_fp.read().strip()


def get_play_store_ver(play_store_url: str) -> str:
    play_store_response = httpx.get(play_store_url)
    play_store_html = lxml.html.fromstring(play_store_response.text)
    play_store_version: str = play_store_html.xpath(PLAY_STORE_XPATH)[0].text
    return play_store_version


def get_app_store_ver(app_store_url: str) -> str:
    app_store_response = httpx.get(app_store_url)
    return str(app_store_response.json()["results"][0]["version"])


def get_app_ver(store: str, url: str) -> str:
    if store == "Play Store":
        return get_play_store_ver(url)
    else:
        return get_app_store_ver(url)


def is_new_ver(new_ver: str, current_ver: str) -> bool:
    for new_num, current_num in zip(new_ver.split("."), current_ver.split(".")):
        if int(new_num) != int(current_num):
            return int(new_num) > int(current_num)
    return False


def send_discord_msg(webhook: str, message: str) -> None:
    webhook_content = {"content": message}
    httpx.post(webhook, data=webhook_content)


def main() -> None:
    current_ver_path = Path("current_ver.json")
    if current_ver_path.exists():
        old_save_data: Dict[str, Dict[str, str]] = json.loads(
            current_ver_path.read_bytes()
        )
    else:
        old_save_data = {
            "NA": {"Play Store": "2.0.0", "App Store": "2.0.0"},
            "JP": {"Play Store": "2.0.0", "App Store": "2.0.0"},
        }

    save_data: Dict[str, Dict[str, str]] = defaultdict(dict)

    for region in ["NA", "JP"]:
        for store in ["Play Store", "App Store"]:
            old_ver = old_save_data[region][store]
            new_ver = get_app_ver(store, STORE_URL[region][store])
            if is_new_ver(new_ver, old_ver):
                message = f"New {region} {store} update: v{new_ver}"
                print(message)
                send_discord_msg(WEBHOOK, message)
                save_data[region][store] = new_ver
            else:
                save_data[region][store] = old_ver

    with open(current_ver_path, "w") as fp:
        json.dump(save_data, fp, indent=2)


if __name__ == "__main__":
    main()
