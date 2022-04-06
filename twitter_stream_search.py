"""Streaming search for twitter"""

import datetime
import socket
import sys
import time
import requests

from twython import TwythonStreamer
from tweetbot_lib import BotTweet


def now():
    """Nicely formatted "now" timestamp"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


class TweetStreamer(TwythonStreamer):
    """Implement on_* methods for parent class TwythonStreamer"""

    def on_success(self, data):  # pylint: disable=no-self-use
        """Success method"""
        if "text" in data:
            name = data["user"]["screen_name"]
            url = f"https://twitter.com/{name}/status/{data['id']}"
            print(f"""\n{now()} {name} {url}\n{data["text"]}""")

    def on_error(
        self, status_code, data
    ):  # pylint: disable=no-self-use,arguments-differ
        """error handling"""
        print(f"{now()}: in on_error")
        print(status_code, data)
        time.sleep(10)
        self.disconnect()

    def on_timeout(
        self, status_code=None, data=None
    ):  # pylint: disable=no-self-use,arguments-differ
        """timeout handling"""
        print(f"{now()}: timeout. {status_code} / {data}")


def main():
    """Scan twitter stream for argument string"""
    if len(sys.argv) > 1:
        track = ",".join(sys.argv[1:])
    else:
        track = "readtheplaque,alwaysreadtheplaque,#readtheplaque,#alwaysreadtheplaque"

    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"Tracking '{track}' starting {start_time}")

    while True:
        try:
            streamer = TweetStreamer(*(BotTweet().twitter_keys))
            streamer.statuses.filter(track=track)
        except requests.exceptions.ChunkedEncodingError:
            # ignore ChunkedEncodingError errors since they're putting a lot of noise on the screen
            time.sleep(60)
        except (
            requests.exceptions.ConnectionError,
            socket.error,
        ) as err:
            print(now(), "restarting ", type(err).__name__, err)
            time.sleep(60)


if __name__ == "__main__":
    main()
