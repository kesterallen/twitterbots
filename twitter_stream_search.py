
import datetime
import requests
import socket
import sys
import time
from twython import TwythonStreamer
from tweetbot_lib import BotTweet

class TweetStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            print now, data['user']['screen_name'], ':', data['text'].encode('utf-8'), "https://twitter.com/{0}/status/{1}".format(data['user']['screen_name'], data['id'])
    
    def on_error(self, status_code, data):
        print "in on_error"
        print status_code, data
        time.sleep(10)
        self.disconnect()

    def on_timeout(self, status_code, data):
        print "in on_timeout"
        print "timeout"


if len(sys.argv) > 1:
    track = ",".join(sys.argv[1:])
else:
    track = "readtheplaque,alwaysreadtheplaque,#readtheplaque,#alwaysreadtheplaque"

print "Tracking '%s'" % track

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
        print "restarting ", err
        time.sleep(60)
