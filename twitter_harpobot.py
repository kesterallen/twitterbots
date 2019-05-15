"""Replier (originally just Harpo Marx) Twitter Bot"""

import argparse
import datetime
import random
import requests
import socket
import sys
import time
from twython import TwythonStreamer, Twython
from twython.exceptions import TwythonError
from tweetbot_lib import BotTweet

DEFAULT_TRACKS = [ # harpo's
    "harpo marx",
    "harpomarx",
    "#harpomarx",
]
DEFAULT_REPLIES = [ # harpo's
    '*hands you a fish*',
    '*hides frog in hat*',
    'Honk honk',
    'Honk honk',
    'Honk honk',
    'Honk honk',
    'Honk honk',
    'Honk honk honk',
    'Honk honk honk',
    'Honk honk honk',
    'Honk honk honk',
    'Honk honk honk',
    '*offers you a lollipop*',
    '*runs after blonde*',
    '*shows you photograph of a horse*',
    '*whistles*',
    '*whistles*',
    '*whistles*',
    '*whistles*',
    '*whistles*',
]

class ReplierSleep(Exception):
    """
    Exception to cause a sleep in the main method, instead of the on_success
    """
    pass

def now():
    """Convenience function to get current time in right format."""
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


class ReplierStreamer(TwythonStreamer):
    """Replier streamer class."""

    def _get_reply(self, data):
        """Extract tweet ID, author, and the reply to it."""
        id = data['id']
        name = data['user']['screen_name']
        url = "https://twitter.com/{0}/status/{1}".format(name, id)
        reply = random.choice(self.replies_arg)
        reply = "@{} {}".format(name, reply)
        return id, url, reply

    def on_success(self, data):
        """Response to successful scan."""
        if 'text' in data:
            id, url, reply = self._get_reply(data)
            print("{} {} {}".format(now(), reply, url))
            twitter = Twython(*(BotTweet().get_keys()))
            try:
                twitter.update_status(status=reply, in_reply_to_status_id=id)
            except TwythonError:
                # Get a non-duplicate reply
                old_reply = reply
                while old_reply == reply:
                    id, url, reply = self._get_reply(data)
                time.sleep(10)
                twitter.update_status(status=reply, in_reply_to_status_id=id)
            raise ReplierSleep()

    def on_error(self, status_code, data):
        """Response to failed scan."""
        print(now(), "in on_error", status_code, "on_error", data)
        time.sleep(90)
        self.disconnect()

    def on_timeout(self, status_code, data):
        """Response to timeout scan."""
        print(now(), status_code, "on_timeout", data)
        time.sleep(90)

def get_args():
    parser = argparse.ArgumentParser(description="Streaming Response Bot")
    parser.add_argument(
        '--track',
        type=str,
        default=",".join(DEFAULT_TRACKS),
        help="comma-separated string of tracking phrases")
    parser.add_argument(
        '--replies',
        type=str,
        default=",".join(DEFAULT_REPLIES),
        help="comma-separated string of replies")
    return parser.parse_args()

def main():

    args = get_args()

    while True:
        try:
            streamer = ReplierStreamer(*(BotTweet().get_keys()))
            streamer.replies_arg = args.replies.split(',')
            streamer.statuses.filter(track=args.track)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            socket.error,
            TwythonError,
        ) as err:
            print("{} restarting: {}".format(now(), err))
            time.sleep(60)
        except ReplierSleep as hts:
            time.sleep(2700)

if __name__ == '__main__':
    main()
