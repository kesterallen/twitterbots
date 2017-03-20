
import datetime
from PIL import Image, ImageOps
import math
import os
import random
from twython import Twython

MAX_TWEET_LEN = 140

class BotTweet(object):

    def __init__(self, word=None):
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
        return " ".join(self.words)

    def publish(self, *keys):
        app_key, app_secret, oauth_token, oauth_token_secret = keys
        twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
        return twitter.update_status(status=self.str)

    def publish_with_image(self, image_fn, *keys):
        app_key, app_secret, oauth_token, oauth_token_secret = keys
        twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
        photo = open(image_fn)
        response = twitter.upload_media(media=photo)
        return twitter.update_status(
            status=self.str, media_ids=[response['media_id']])

def get_tweet_file(filename):
    """ Assume the text file is in ../txt """
    return os.path.join(os.path.dirname(__file__), '../txt/', filename)

def tweetify_text(textfile):
    """
    Break the input string 'text' into 140-char-or-less BotTweet objects.
    """
    # Read file into 'words' list:
    #
    with open(textfile) as text_fh:
        text = text_fh.read()
    words = text.split()

    tweet = BotTweet()
    tweets = []
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

def get_keys(bot_filename, keyfile="keys.txt"):
    keyfile_full = os.path.join(
        os.path.dirname(__file__), '..', keyfile)

    auth_keys = {}
    with open(keyfile_full) as keys_fh:
        for row in keys_fh.readlines():
            name, value = row.strip().split('=')
            auth_keys[name] = value
    keynames = ['APP_KEY', 'APP_SEC', 'OAUTH_TOKEN', 'OAUTH_TOKEN_SEC']
    key_prefix = os.path.basename(bot_filename)
    keys = [auth_keys["%s%s" % (key_prefix, kn)] for kn in keynames]
    return keys
