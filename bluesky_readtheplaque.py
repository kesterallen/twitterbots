"""Set the featured plaque for the day and tweet about it"""

from box import Box
import requests
from blueskybot_lib import BotPost

PREFIX = "https://readtheplaque.com"
URL = f"{PREFIX}/api/plaques/random"


def main():
    if BotPost.run_recently(seconds=86400, botname="bluesky_readtheplaque"):
        return

    resp = requests.get(URL)
    plaque = Box(resp.json())

    post = f"""
{plaque.title} 
#alwaysreadtheplaque
{PREFIX}/plaque/{plaque.slug}
{PREFIX}{plaque.thumb_url}
"""
    client = BotPost(post)
    client.publish()


if __name__ == "__main__":
    main()
