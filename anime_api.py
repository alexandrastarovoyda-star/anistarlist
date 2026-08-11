import requests


def get_anime_page(page=1):
    response = requests.get(
        "https://api.jikan.moe/v4/anime",
        params={"page": page}
    )

    if response.status_code != 200:
        print("Jikan error:", response.status_code)
        return None

    return response.json()
