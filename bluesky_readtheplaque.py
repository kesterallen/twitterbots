"""Set the featured plaque for the day and tweet about it"""

from box import Box
import requests
from blueskybot_lib import BotPost

PREFIX = "https://readtheplaque.com"
URL = f"{PREFIX}/api/plaques/random"


def main():
    if BotPost.run_recently(seconds=86400, botname="readtheplaque"):
        return

    resp = requests.get(URL)
    plaque = Box(resp.json())

    client = BotPost(f"{plaque.title} #alwaysreadtheplaque")
    client.publish_with_link_card(f"{PREFIX}/plaque/{plaque.slug}")


if __name__ == "__main__":
    main()
