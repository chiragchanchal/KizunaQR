import urllib.request
import os

FONTS = {
    "inter.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/static/Inter-Regular.ttf",
    "playfair.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/static/PlayfairDisplay-Regular.ttf",
    "caveat.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/caveat/static/Caveat-Regular.ttf"
}

os.makedirs("static/fonts", exist_ok=True)

for name, url in FONTS.items():
    dest = os.path.join("static", "fonts", name)
    print(f"Downloading {name}...")
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"Saved {name}")
    except Exception as e:
        print(f"Error downloading {name}: {e}")
