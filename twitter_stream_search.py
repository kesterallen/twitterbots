
import requests
import sys
import time
from twython import TwythonStreamer
from tweetbot_lib import get_keys

class TweetStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            print data['user']['screen_name'], ':', data['text'].encode('utf-8'), "https://twitter.com/{0}/status/{1}".format(data['user']['screen_name'], data['id'])
            print
    
    def on_error(self, status_code, data):
        print "in on_error"
        print status_code, data
        time.sleep(1)
        self.disconnect()

    def on_timeout(self, status_code, data):
        print "in on_timeout"
        print "timeout"

keys = get_keys(__file__)

if len(sys.argv) > 1:
    track = ",".join(sys.argv[1:])
else:
    track = "readtheplaque,alwaysreadtheplaque,#readtheplaque,#alwaysreadtheplaque"

print "Tracking '%s'" % track

while True:
    try:
        streamer = TweetStreamer(keys[0], keys[1], keys[2], keys[3])
        streamer.statuses.filter(track=track)
    except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError):
        print "restarting"
        time.sleep(10)
