
import datetime
import requests
import socket
import sys
import time
from twython import TwythonStreamer
from tweetbot_lib import BotTweet

def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

class TweetStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            name = data['user']['screen_name']
            url = "https://twitter.com/{0}/status/{1}".format(name, data['id'])
            text = data['text'].encode('utf-8')
            print("{} {}: {} {}".format(now(), name, text, url))
    
    def on_error(self, status_code, data):
        print(now(), "in on_error")
        print(status_code, data)
        time.sleep(10)
        self.disconnect()

    def on_timeout(self, status_code, data):
        print(now(), "timeout")


if len(sys.argv) > 1:
    track = ",".join(sys.argv[1:])
else:
    track = "readtheplaque,alwaysreadtheplaque,#readtheplaque,#alwaysreadtheplaque"

print("Tracking '{}'".format(track))

keys = BotTweet().get_keys()
while True:
    try:
        streamer = TweetStreamer(keys[0], keys[1], keys[2], keys[3])
        streamer.statuses.filter(track=track)
    except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            socket.error,
        ) as err:
        print(now(), "restarting ", type(err).__name__, err)
        time.sleep(60)
