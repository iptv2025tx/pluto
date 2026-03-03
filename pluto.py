
import requests
import uuid
import os
from datetime import datetime, timedelta, timezone

# =============================
# CONFIGURATION
# =============================

STITCHER = "https://cfd-v4-service-channel-stitcher-use1-1.prd.pluto.tv"

# Order: English countries first, then alphabetical
REGIONS = {
    "United States": "108.82.206.181",
    "Canada": "192.206.151.131",
    "United Kingdom": "178.238.11.6",
    "Argentina": "168.226.232.228",
    "Brazil": "104.112.149.255",
    "Chile": "200.89.74.146",
    "Denmark": "192.36.27.7",
    "France": "91.160.93.4",
    "Germany": "85.214.132.117",
    "Italy": "80.207.161.250",
    "Mexico": "201.144.119.146",
    "Norway": "160.68.205.231",
    "Spain": "88.26.241.248",
    "Sweden": "192.44.242.19"
}

EPG_URL = "https://github.com/matthuisman/i.mjh.nz/raw/master/PlutoTV/all.xml.gz"

# =============================
# TIME FORMAT
# =============================

def format_time(dt):
    return dt.replace(minute=0, second=0, microsecond=0) \
             .isoformat() \
             .replace("+00:00", "Z")

# =============================
# AUTHENTICATION
# =============================

def authenticate(region_ip):
    device_id = str(uuid.uuid4())

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Forwarded-For": region_ip,
        "X-Real-IP": region_ip,
        "CF-Connecting-IP": region_ip
    }

    boot_url = (
        "https://boot.pluto.tv/v4/start?"
        "appName=web"
        "&appVersion=8.0.0"
        "&deviceVersion=122.0.0"
        "&deviceModel=web"
        "&deviceMake=chrome"
        "&deviceType=web"
        f"&clientID={device_id}"
        "&clientModelNumber=1.0.0"
        "&serverSideAds=false"
        "&drmCapabilities=widevine:L3"
        f"&username={USERNAME}"
        f"&password={PASSWORD}"
    )

    r = requests.get(boot_url, headers=headers, timeout=30)
    data = r.json()

    return data.get("sessionToken"), data.get("stitcherParams", ""), headers

# =============================
# FETCH CHANNELS
# =============================

def fetch_channels(headers):
    now = datetime.now(timezone.utc)
    later = now + timedelta(hours=6)

    start = format_time(now)
    stop = format_time(later)

    url = f"https://api.pluto.tv/v2/channels?start={start}&stop={stop}"

    r = requests.get(url, headers=headers, timeout=30)
    data = r.json()

    if not isinstance(data, list):
        print("Unexpected API response:", data)
        return []

    return data

# =============================
# BUILD PLAYLIST
# =============================

def build_playlist():
    playlist = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'

    for country_name, ip in REGIONS.items():
        print(f"Generating {country_name} channels...")

        token, stitcher_params, headers = authenticate(ip)

        if not token:
            print("Authentication failed:", country_name)
            continue

        channels = fetch_channels(headers)
        print(f"{country_name} channel count:", len(channels))

        for ch in channels:
            if not isinstance(ch, dict):
                continue

            if not ch.get("isStitched"):
                continue

            name = ch.get("name", "Unknown")
            slug = ch.get("slug", "")
            logo = ch.get("colorLogoPNG", {}).get("path", "")

            stream_url = (
                f"{STITCHER}/v2/stitch/hls/channel/{ch['_id']}/master.m3u8"
                f"?{stitcher_params}&jwt={token}&masterJWTPassthrough=true"
            )

            tvg_id = f"{country_name}-{slug}"

            playlist += (
                f'#EXTINF:-1 group-title="{country_name}" '
                f'tvg-id="{tvg_id}" '
                f'tvg-name="{name}" '
                f'tvg-logo="{logo}",{name}\n'
            )

            playlist += stream_url + "\n\n"

    return playlist

# =============================
# MAIN
# =============================

def main():
    m3u = build_playlist()

    # Normalize line endings for IPTV compatibility
    m3u = m3u.replace("\r\n", "\n")

    with open("pluto_global.m3u", "wb") as f:
        f.write(m3u.encode("utf-8"))

    print("\nPlaylist created: pluto_global.m3u")

if __name__ == "__main__":
    main()


