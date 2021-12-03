"""Replier (originally just Harpo Marx) Twitter Bot"""

import argparse
import datetime
import random
import socket
import time

import requests
from twython import TwythonStreamer, Twython
from twython.exceptions import TwythonError
from tweetbot_lib import BotTweet


SLEEP_ERROR = 90
SLEEP_TWEET = 2700
SLEEP_DUPLICATE = 10

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

def now():
    """Convenience function to get current time in right format."""
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


class ReplierStreamer(TwythonStreamer):
    """Replier streamer class."""
    def __init__(self, keys, args):
        super().__init__(*keys)
        self.keys = keys
        self.track = args.track
        self.replies = args.replies.split(',')
        self.sendtweet = args.sendtweet
        self.sleep_error = args.sleep_error
        self.sleep_tweet = args.sleep_tweet
        self.sleep_duplicate = args.sleep_duplicate

    def _get_reply(self, data):
        """Extract tweet ID, author, and the reply to it."""
        st_id = data['id']
        name = data['user']['screen_name']
        url = f"https://twitter.com/{name}/status/{st_id}"
        reply = random.choice(self.replies)
        reply = f"@{name} {reply}"
        return st_id, url, reply

    def on_success(self, data):
        """Response to successful scan."""
        if 'text' in data:
            st_id, url, reply = self._get_reply(data)
            print(f"{now()} {reply} {url}")
            twy = Twython(*(self.keys))
            try:
                if self.sendtweet:
                    twy.update_status(status=reply, in_reply_to_status_id=st_id)
                else:
                    print(f"Debug: supressing tweet '{reply}'")
            except TwythonError:
                # Twitter rejects duplicate replies, get a non-duplicate one:
                old_reply = reply
                while old_reply == reply:
                    _, _, reply = self._get_reply(data)
                time.sleep(SLEEP_DUPLICATE)
                if self.sendtweet:
                    twy.update_status(status=reply, in_reply_to_status_id=st_id)
                else:
                    print(f"Debug: skip duplicate tweet '{reply}'")
            raise ReplierSleep()

    def on_error(self, status_code, data):
        """Response to failed scan."""
        print(f"{now()} in on_error: {status_code} {data}")
        time.sleep(SLEEP_ERROR)
        self.disconnect()

    def on_timeout(self):
        """Response to timeout scan."""
        print(f"{now()} in on_timeout")
        time.sleep(SLEEP_ERROR)

def get_args():
    """Parse the cli args"""
    parser = argparse.ArgumentParser(
        description="Streaming Response Bot. Defaults to @HarpoBot"
    )
    parser.add_argument(
        '--track',
        type=str,
        default=",".join(DEFAULT_TRACKS),
        help="comma-separated string of tracking phrases")
    parser.add_argument(
        '--replies',
        type=str,
        default=",".join(DEFAULT_REPLIES),
        help="comma-separated string of replies",)
    parser.add_argument(
        '--botname',
        type=str,
        default="twitter_harpobot.py",
        help="bot filename (used for determining which keys to use)",)
    parser.add_argument(
        '--sendtweet',
        type=lambda s: s.lower() in ['true', 't', 'yes', 'y', '1'],
        default=True,
        help="Set this to False for non-tweeting debug mode",)
    parser.add_argument(
        '--sleep_error',
        type=int,
        default=SLEEP_ERROR,
        help='Number of seconds to sleep after an error',)
    parser.add_argument(
        '--sleep_tweet',
        type=int,
        default=SLEEP_TWEET,
        help='Number of seconds to sleep after a successful tweet',)
    parser.add_argument(
        '--sleep_duplicate',
        type=int,
        default=SLEEP_DUPLICATE,
        help='Number of seconds to sleep after attempting a duplicate tweet',)

    return parser.parse_args()

def main():
    """Run Streamer"""
    args = get_args()
    keys = BotTweet(botname=args.botname).get_keys()

    while True:
        try:
            streamer = ReplierStreamer(keys, args)
            streamer.statuses.filter(track=streamer.track)
        except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
                socket.error,
                TwythonError,
        ) as err:
            time.sleep(SLEEP_ERROR)
        except ReplierSleep:
            time.sleep(SLEEP_TWEET)

if __name__ == '__main__':
    main()
