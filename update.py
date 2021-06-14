import json
import time
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Dict

import httpx
import lxml.html


class Region(str, Enum):
    NA = "NA"
    JP = "JP"


class Store(str, Enum):
    PLAY_STORE = "Google Play Store"
    APP_STORE = "iOS App Store"


STORE_URL = {
    Region.NA: {
        Store.APP_STORE: "https://itunes.apple.com/lookup?bundleId=com.aniplex.fategrandorder.en&country=us",
        Store.PLAY_STORE: "https://play.google.com/store/apps/details?id=com.aniplex.fategrandorder.en",
    },
    Region.JP: {
        Store.APP_STORE: "https://itunes.apple.com/lookup?bundleId=com.aniplex.fategrandorder&country=jp",
        Store.PLAY_STORE: "https://play.google.com/store/apps/details?id=com.aniplex.fategrandorder",
    },
}
AVATAR_URL = {
    Store.PLAY_STORE: "https://i.imgur.com/kN7NO37.png",  # From the PLay Store apk P5w.png
    Store.APP_STORE: "https://i.imgur.com/fTxPeCW.png",  # https://www.apple.com/app-store/
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"
PLAY_STORE_XPATH = "/html/body/div[1]/div[4]/c-wiz/div/div[2]/div/div/main/c-wiz[4]/div[1]/div[2]/div/div[4]/span/div/span"
APP_STORE_XPATH = "/html/body/div[1]/div[4]/main/div/section[4]/div[2]/div[1]/div/p"
HEADERS = {"user-agent": USER_AGENT}


def get_website_ver(play_store_url: str, xpath: str) -> str:
    response = httpx.get(play_store_url)
    site_html = lxml.html.fromstring(response.text)
    try:
        version_string: str = site_html.xpath(xpath)[0].text
        return version_string.replace("バージョン", "").replace("Version", "").strip()
    except:
        return "2.0.0"


def get_app_store_ver(app_store_url: str) -> str:
    app_store_response = httpx.get(app_store_url + f"&time={int(time.time())}")
    app_detail = app_store_response.json()["results"][0]
    api_version = str(app_detail["version"])
    app_store_site_url = str(app_detail["trackViewUrl"]).split("?")[0]
    app_store_version = get_website_ver(app_store_site_url, APP_STORE_XPATH)
    if is_new_ver(api_version, app_store_version):
        return api_version
    else:
        if api_version != app_store_version:
            print("App store website version is newer than api version")
        return app_store_version


def get_app_ver(store: str, url: str) -> str:
    if store == Store.PLAY_STORE:
        return get_website_ver(url, PLAY_STORE_XPATH)
    else:
        return get_app_store_ver(url)


def is_new_ver(new_ver: str, current_ver: str) -> bool:
    try:
        for new_num, current_num in zip(new_ver.split("."), current_ver.split(".")):
            if int(new_num) != int(current_num):
                return int(new_num) > int(current_num)
    except ValueError:
        return False
    return False


def main(webhook: str) -> None:
    current_ver_path = Path("current_ver.json")
    if current_ver_path.exists():
        old_save_data: Dict[str, Dict[str, str]] = json.loads(
            current_ver_path.read_bytes()
        )
    else:
        old_save_data = {
            Region.NA: {Store.PLAY_STORE: "2.0.0", Store.APP_STORE: "2.0.0"},
            Region.JP: {Store.PLAY_STORE: "2.0.0", Store.APP_STORE: "2.0.0"},
        }

    save_data: Dict[Region, Dict[Store, str]] = defaultdict(dict)

    for region in [Region.NA, Region.JP]:
        for store in [Store.APP_STORE]:
            old_ver = old_save_data[region][store]
            new_ver = get_app_ver(store, STORE_URL[region][store])
            if is_new_ver(new_ver, old_ver):
                message = f"{region} update: v{new_ver}"
                print(message)
                webhook_content = {
                    "content": message,
                    "username": store.value,
                    "avatar_url": AVATAR_URL[store],
                }
                httpx.post(webhook, data=webhook_content)
                save_data[region][store] = new_ver
            else:
                save_data[region][store] = old_ver

    with open(current_ver_path, "w") as fp:
        json.dump(save_data, fp, indent=2)


if __name__ == "__main__":
    with open("WEBHOOK.url", encoding="utf-8") as webhook_fp:
        webhook_url = webhook_fp.read().strip()
    main(webhook_url)
