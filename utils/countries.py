import json

COUNTRY_FILE = "countries.json"


def load_countries():
    with open(COUNTRY_FILE) as f:
        return json.load(f)


def save_countries(data):
    with open(COUNTRY_FILE, "w") as f:
        json.dump(data, f, indent=2)
