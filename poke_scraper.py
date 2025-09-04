#!/usr/bin/env python3
# poke_scraper.py
import argparse
import os
import time
import re
import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://bulbapedia.bulbagarden.net"
LIST_URL = BASE + "/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

def get_pokemon_list(delay=1):
    resp = requests.get(LIST_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    entries = []

    tables = soup.find_all("table", {"class": re.compile(r"(roundy|sortable)")})
    for table in tables:
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            dex_text = tds[0].get_text(strip=True)
            m = re.search(r"\d+", dex_text)
            if not m:
                continue
            dex = int(m.group())
            a = tr.find("a", href=True)
            if not a:
                continue
            name = a.get_text(strip=True)
            link = urljoin(BASE, a["href"])
            entries.append((dex, name, link))
        time.sleep(delay)
    return entries

def get_pokemon_image(url):
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    infobox = soup.find("table", {"class": re.compile(r"infobox|roundy")})
    img = infobox.find("img") if infobox else None
    if img and img.get("src"):
        src = img["src"]
        if src.startswith("//"):
            src = "https:" + src
        return src
    return None

def download_image(img_url, filename):
    resp = requests.get(img_url)
    resp.raise_for_status()
    with open(filename, "wb") as f:
        f.write(resp.content)

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    os.makedirs("downloads", exist_ok=True)
    pokemons = get_pokemon_list()

    for dex, name, url in pokemons:
        logging.info("Processing #%04d %s", dex, name)
        img_url = get_pokemon_image(url)
        if not img_url:
            logging.warning("No image for %s", name)
            continue
        ext = os.path.splitext(urlparse(img_url).path)[-1] or ".png"
        filename = f"downloads/{dex:04d}-{name}{ext}"
        download_image(img_url, filename)
        logging.info("Saved %s", filename)

if __name__ == "__main__":
    main()
