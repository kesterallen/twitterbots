"""Set the featured plaque for the day and tweet about it"""

from box import Box
import requests
from blueskybot_lib import BotPost

PREFIX = "https://readtheplaque.com"
URL = f"{PREFIX}/api/plaques/random"


def main():
    if BotPost.run_recently("readtheplaque"):
        return

    resp = requests.get(URL)
    plaque = Box(resp.json())

    post = BotPost(f"{plaque.title} #alwaysreadtheplaque")
    post.publish_with_link_card(f"{PREFIX}/plaque/{plaque.slug}")


if __name__ == "__main__":
    main()
