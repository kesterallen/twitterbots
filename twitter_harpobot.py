
import datetime
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

# Throw one of these to sleep in the main method, instead of the on_success
class HarpoSleep(Exception):
    pass

def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

def get_reply(data):
    id = data['id']
    name = data['user']['screen_name']
    url = "https://twitter.com/{0}/status/{1}".format(name, id)
    reply = "@{} {}".format(data['user']['screen_name'], random.choice(replies))
    return id, url, reply

class HarpoStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            id, url, reply = get_reply(data)
            print("{} {} {}".format(now(), reply, url))
            twitter = Twython(*keys)
            try:
                twitter.update_status(status=reply, in_reply_to_status_id=id)
            except TwythonError:
                # Get a non-duplicate reply
                old_reply = reply
                while old_reply == reply:
                    id, url, reply = get_reply(data)
                time.sleep(10)
                twitter.update_status(status=reply, in_reply_to_status_id=id)
            raise HarpoSleep()

    def on_error(self, status_code, data):
        print(now(), "in on_error", status_code, "on_error", data)
        time.sleep(90)
        self.disconnect()

    def on_timeout(self, status_code, data):
        print(now(), status_code, "on_timeout", data)
        time.sleep(90)

def main():
    if len(sys.argv) > 1:
        track = ",".join(sys.argv[1:])
    else:
        track = "harpo marx,harpomarx,#harpomarx"

    while True:
        try:
            streamer = HarpoStreamer(*keys)
            streamer.statuses.filter(track=track)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            socket.error,
            TwythonError,
        ) as err:
            print(now(), "restarting ", err)
            time.sleep(60)
        except HarpoSleep as hts:
            time.sleep(2700)
    
if __name__ == '__main__':
    main()
