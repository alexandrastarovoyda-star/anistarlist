# file for import iformaition into anime.db from anime-offline-database-minified.json

import requests
from cs50 import SQL
import json
import re

db = SQL("sqlite:///anime.db")

with open("anime-offline-database-minified.json", "r", encoding="utf-8") as file:
    data = json.load(file)


for anime in data["data"][30000:]:
    mal_id = None
    for source in anime["sources"]:
        match = re.search(r"myanimelist\.net/anime/(\d+)", source)
        if match:
            mal_id = int(match.group(1))
            break

    if mal_id is None:
        continue

    existing = db.execute(
        "SELECT id FROM titels WHERE mal_id = ?",
        mal_id
    )
    if len(existing) == 0:
        db.execute("INSERT INTO titels (mal_id, Title, Episodes, image_url, trailer_url, Description) VALUES (?, ?, ?, ?, ?, ?)",
                   mal_id,
                   anime["title"],
                   anime["episodes"],
                   anime["picture"],
                   None,
                   None)
