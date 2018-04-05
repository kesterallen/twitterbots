
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

track_phrases = [
    "San Francisco housing crisis",
    # Add more here
]
replies = [
    "San Francisco's population density is lower than Queens's",
    "San Francisco's has more land and a lower population density than Paris",
    # Add more here
]

class YimbySleep(Exception):
    """Throw one of these to sleep in the main method, instead of the on_success"""
    pass

def current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

def get_reply(data):
    reply = "@%s %s" % (data['user']['screen_name'], random.choice(replies))
    return reply

class YimbyStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            reply = get_reply(data)
            print current_time(), reply, \
                "https://twitter.com/{0}/status/{1}".format(data['user']['screen_name'], data['id'])
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
            raise YimbySleep()

    def on_error(self, status_code, data):
        print current_time(), "in on_error", status_code, "on_error", data
        time.sleep(1)
        self.disconnect()

    def on_timeout(self, status_code, data):
        print current_time(), status_code, "on_timeout", data
        time.sleep(1)

def main():
    if len(sys.argv) > 1:
        track_phrases = sys.argv[1:]

    track = ",".join(track_phrases)

    while True:
        try:
            streamer = YimbyStreamer(keys[0], keys[1], keys[2], keys[3])
            streamer.statuses.filter(track=track)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            socket.error,
            TwythonError,
        ) as err:
            print current_time(), "restarting ", err
            time.sleep(60)
        except YimbySleep as ys_err:
            time.sleep(2700)
    
if __name__ == '__main__':
    main()
