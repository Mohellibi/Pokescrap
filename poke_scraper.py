#!/usr/bin/env python3
# poke_scraper_ec2.py
import argparse
import os
import time
import re
import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import boto3
from botocore.exceptions import BotoCoreError, ClientError

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

def upload_to_s3(bucket, key, data, public=False):
    if bucket != "bucket-pokemon2":
        raise ValueError("Only bucket-pokemon2 is allowed")
    if not key.startswith("images/"):
        raise ValueError("Key must start with 'images/'")

    s3 = boto3.client("s3")
    extra_args = {"ContentType": "image/png"}
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=data, **extra_args)
        return True
    except (BotoCoreError, ClientError) as e:
        logging.error("Failed to upload %s: %s", key, e)
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", default="bucket-pokemon2", help="Target S3 bucket name")
    parser.add_argument("--prefix", default="images", help="S3 key prefix")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of Pokémon (for testing)")
    args = parser.parse_args()

    pokemons = get_pokemon_list()

    if args.limit:
        pokemons = pokemons[:args.limit]

    logging.info("Found %d Pokémon entries", len(pokemons))

    for dex, name, url in pokemons:
        logging.info("Processing #%04d %s", dex, name)
        img_url = get_pokemon_image(url)
        if not img_url:
            logging.warning("No image for %s", name)
            continue

        resp = requests.get(img_url)
        resp.raise_for_status()
        filename = f"{dex:04d}-{name}{os.path.splitext(urlparse(img_url).path)[-1]}"
        s3_key = f"{args.prefix}/{filename}"

        if upload_to_s3(args.bucket, s3_key, resp.content):
            logging.info("Uploaded to s3://%s/%s", args.bucket, s3_key)

if __name__ == "__main__":
    main()
