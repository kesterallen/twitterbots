"""Streaming search (grep) for twitter"""

import datetime
import socket
import sys
import time

import requests
from twython import TwythonStreamer
from tweetbot_lib import BotTweet

def now():
    """Nicely formatted "now" timestamp"""
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

class TweetStreamer(TwythonStreamer):
    """Implement on_* methods for parent class TwythonStreamer"""
    def on_success(self, data): #pylint: disable=no-self-use
        """Success method"""
        if 'text' in data:
            name = data['user']['screen_name']
            url = "https://twitter.com/{0}/status/{1}".format(name, data['id'])
            text = data['text']
            print("\n{} {} {}\n{}".format(now(), name, url, text))

    def on_error(self, status_code, data): #pylint: disable=no-self-use
        """error handling"""
        print("{}: in on_error".format(now()))
        print(status_code, data)
        time.sleep(10)
        self.disconnect()

    def on_timeout(self, status_code=None, data=None): #pylint: disable=no-self-use
        """timeout handling"""
        print("{}: timeout. {} / {}".format(now(), status_code, data))

def main():
    """Scan twitter stream for argument string"""
    if len(sys.argv) > 1:
        track = ",".join(sys.argv[1:])
    else:
        track = "readtheplaque,alwaysreadtheplaque,#readtheplaque,#alwaysreadtheplaque"

    print("Tracking '{}'".format(track))

    while True:
        try:
            streamer = TweetStreamer(*(BotTweet().get_keys()))
            streamer.statuses.filter(track=track)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            socket.error,
        ) as err:
            print(now(), "restarting ", type(err).__name__, err)
            time.sleep(60)

if __name__ == '__main__':
    main()
