
import datetime
import inspect
import os
import requests
from twython import Twython

MAX_TWEET_LEN = 140

class BotTweet(object):

    def __init__(self, word=None, bot_filename=None):
        if bot_filename is None:
            fullname = inspect.stack()[-1][1] #original calling script's filename
            self.bot_filename = os.path.basename(fullname)
        else:
            self.bot_filename = bot_filename
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
        key_prefix = os.path.basename(self.bot_filename)
        keys = [auth_keys["%s%s" % (key_prefix, kn)] for kn in keynames]
        return keys

    def publish(self):
        app_key, app_secret, oauth_token, oauth_token_secret = self.get_keys()
        twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
        return twitter.update_status(status=self.str)

    def publish_with_image(self, image_fn):
        app_key, app_secret, oauth_token, oauth_token_secret = self.get_keys()
        twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
        with open(image_fn) as photo:
            response = twitter.upload_media(media=photo)
        return twitter.update_status(
            status=self.str, media_ids=[response['media_id']])

    def download_tweet_text(self, tweet_generate_url):
        resp = requests.get(tweet_generate_url)
        text = resp.json()['tweet']
        self.words = [text]

def get_tweet_file(filename):
    """ Assume the text file is in ../txt/ """
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

def parse_text_and_get_today_tweet(textfile, start_date):
    tweetfile = get_tweet_file(textfile)
    tweets = tweetify_text(tweetfile)
    today_index = get_today_index(len(tweets), start_date)
    today_tweet = tweets[today_index]
    return today_tweet
