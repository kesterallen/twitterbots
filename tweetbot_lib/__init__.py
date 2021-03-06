"""Module to tweet for bots"""

import datetime
import inspect
import os
import requests
from twython import Twython

MAX_TWEET_LEN = 140

class BotTweet:
    """Bot tweet module"""

    def __init__(self, word=None, botname=None):
        if botname is None:
            fullname = inspect.stack()[-1][1] #original calling script's filename
            self.botname = os.path.basename(fullname)
        else:
            self.botname = botname

        self.words = [] if word is None else [word]

    def pop(self):
        return self.words.pop()

    def append(self, word):
        self.words.append(word)

    @property
    def is_too_long(self):
        return self.len > MAX_TWEET_LEN

    @property
    def len(self):
        return len(self.str)

    @property
    def str(self):
        return " ".join(self.words)

    def __repr__(self):
        return self.str

    def get_keys(self, keyfile="../keys.txt"):
        """Assume the keys file is ../keys.txt"""
        keyfile_full = os.path.join(
            os.path.dirname(__file__), keyfile)

        auth_keys = {}
        with open(keyfile_full) as keys_fh:
            for row in keys_fh.readlines():
                name, value = row.strip().split('=')
                auth_keys[name] = value
        keynames = ['APP_KEY', 'APP_SEC', 'OAUTH_TOKEN', 'OAUTH_TOKEN_SEC']
        key_prefix = os.path.basename(self.botname)
        keys = [auth_keys["{}{}".format(key_prefix, kn)] for kn in keynames]
        return keys

    def publish(self, debug=False):
        app_key, app_secret, oauth_token, oauth_token_secret = self.get_keys()
        twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
        if debug:
            print(self.str)
            return self.str
        else:
            return twitter.update_status(status=self.str)

    def publish_with_image(self, image_fn, debug=False):
        app_key, app_secret, oauth_token, oauth_token_secret = self.get_keys()
        twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
        with open(image_fn, 'rb') as image:
            response = twitter.upload_media(media=image)
        if debug:
            print(response)
        return twitter.update_status(
            status=self.str, media_ids=[response['media_id']])

    def download_tweet_text(self, tweet_generate_url):
        resp = requests.get(tweet_generate_url)
        text = resp.json()['tweet']
        self.words = [text]

def get_tweet_filename(filename):
    """ Assume the text file is in ../txt/ """
    return os.path.join(os.path.dirname(__file__), '../txt/', filename)

def tweetify_text(textfile, use_lines=False):
    """
    Break the input string 'text' into MAX_TWEET_LEN-char-or-less BotTweet objects.

    If use_lines is True, make one tweet per line in the file; otherwise
    """
    tweets = []
    if use_lines:
        # One line per tweet
        with open(textfile) as text_fh:
            lines = text_fh.readlines()
            for line in lines:
                if len(line) > MAX_TWEET_LEN:
                    line = line[:MAX_TWEET_LEN]
                    print("trimming to {} chars: {}".format(MAX_TWEET_LEN, line))
                tweet = BotTweet(line)
                tweets.append(tweet)
    else:
        # Read file into 'words' list:
        #
        with open(textfile) as text_fh:
            text = text_fh.read()
        words = text.split()

        tweet = BotTweet()
        # Break the text into tweet-sized chunks:
        #
        for word in words:
            if tweet.is_too_long:
                extra_word = tweet.pop()
                tweets.append(tweet)
                tweet = BotTweet(extra_word)

            tweet.append(word)

        # Get the last tweet:
        #
        tweets.append(tweet)

    return tweets

def get_today_index(num_tweets, then):
    now = datetime.datetime.now()
    td_since_start = now - then
    today_index = td_since_start.days % num_tweets
    return today_index

def get_today_tweet(tweets, then):
    today_index = get_today_index(len(tweets), then)
    today_tweet = tweets[today_index]
    return today_tweet

def parse_text_and_get_today_tweet(textfile, start_date, use_lines=False):
    tweetfile = get_tweet_filename(textfile)
    tweets = tweetify_text(tweetfile, use_lines)
    return get_today_tweet(tweets, start_date)
