# file for import extra iformaition into anime.db from anime-offline-database-minified.json

import requests
from cs50 import SQL
import json
import re

db = SQL("sqlite:///anime.db")

with open("anime-offline-database-minified.json", "r", encoding="utf-8") as file:
    data = json.load(file)


for anime in data["data"][8500:]:
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
    if len(existing) != 0:
        db.execute("UPDATE titels SET year = ?, season = ?, score = ? WHERE mal_id = ?",
                   anime.get("animeSeason", {}).get("year"),
                   anime.get("animeSeason", {}).get("season"),
                   anime.get("score", {}).get("arithmeticMean"),
                   mal_id)
