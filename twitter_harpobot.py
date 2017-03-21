
import requests
import sys
import random
import datetime
import time
from twython import TwythonStreamer, Twython
from twython.exceptions import TwythonError
from tweetbot_lib import BotTweet

keys = BotTweet().get_keys()

replies = [
    'Honk honk honk',
    'Honk honk',
    '*whistles*',
    'Honk honk honk',
    'Honk honk',
    '*whistles*',
    'Honk honk honk',
    'Honk honk',
    '*whistles*',
    'Honk honk honk',
    'Honk honk',
    '*whistles*',
    'Honk honk honk',
    'Honk honk',
    '*whistles*',
    '*runs after blonde*',
    '*shows you photograph of a horse*',
    '*hands you a fish*',
    '*hides frog in hat*',
    '*offers you a lollipop*',
]

def get_reply(data):
    reply = "@%s %s" % (data['user']['screen_name'], random.choice(replies))
    return reply

class HarpoStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            reply = get_reply(data)
            print datetime.datetime.now(), reply
            twitter = Twython(keys[0], keys[1], keys[2], keys[3])
            try:
                twitter.update_status(status=reply, in_reply_to_status_id=data['id'])
            except TwythonError:
                # Get a non-duplicate reply
                old_reply = reply
                while old_reply == reply:
                    reply = get_reply(data)
                time.sleep(1)
                twitter.update_status(status=reply, in_reply_to_status_id=data['id'])
            time.sleep(3600)
    
    def on_error(self, status_code, data):
        print "in on_error"
        print status_code, data
        time.sleep(1)
        self.disconnect()

    def on_timeout(self, status_code, data):
        print status_code, "timeout", data
        time.sleep(1)

def main():
    if len(sys.argv) > 1:
        track = ",".join(sys.argv[1:])
    else:
        track = "harpo marx,harpomarx,#harpomarx"

    while True:
        try:
            streamer = HarpoStreamer(keys[0], keys[1], keys[2], keys[3])
            streamer.statuses.filter(track=track)
        except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError):
            print "restarting"
            time.sleep(10)

if __name__ == '__main__':
    main()
