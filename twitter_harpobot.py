
import datetime
from pprint import pprint
import random
import requests
import socket
import sys
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

def current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

def get_reply(data):
    reply = "@%s %s" % (data['user']['screen_name'], random.choice(replies))
    return reply

class HarpoStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            reply = get_reply(data)
            print current_time(), reply
            twitter = Twython(keys[0], keys[1], keys[2], keys[3])
            try:
                twitter.update_status(status=reply, in_reply_to_status_id=data['id'])
            except TwythonError:
                # Get a non-duplicate reply
                old_reply = reply
                while old_reply == reply:
                    reply = get_reply(data)
                time.sleep(10)
                twitter.update_status(status=reply, in_reply_to_status_id=data['id'])
            time.sleep(2700)
    
    def on_error(self, status_code, data):
        print current_time(), "in on_error", status_code, "on_error", data
        time.sleep(1)
        self.disconnect()

    def on_timeout(self, status_code, data):
        print current_time(), status_code, "on_timeout", data
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
        except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
                socket.error,
            ) as err:
            print current_time(), "restarting ", err
            time.sleep(60)

if __name__ == '__main__':
    main()
