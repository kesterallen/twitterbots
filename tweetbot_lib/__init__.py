"""Module to tweet for bots"""

import datetime
import inspect
import os
from mastodon import Mastodon
import requests
from twython import Twython

MAX_TWEET_LEN = 140

MASTODON_API_BASE_URL = "https://botsin.space/"


class BotTweet:
    """Bot tweet module"""

    def __init__(self, word=None, botname=None):
        """Truncate word to MAX_TWEET_LEN if necessary"""
        if botname is None:
            frameinfo = inspect.stack()[-1]
            self.botname = os.path.basename(frameinfo.filename)
        else:
            self.botname = botname

        self.words = [] if word is None else [word[:MAX_TWEET_LEN]]

    def pop(self):
        """Pop a word off of self.words"""
        return self.words.pop()

    def append(self, word):
        """Append 'word' to the self.words list, truncating if necessary"""
        self.words.append(word[:MAX_TWEET_LEN])

    def can_take_new_word(self, word):
        """Will tweet be under the length limit after adding a new word"""
        return not self.will_be_too_long(word)

    def will_be_too_long(self, word):
        """Will tweet be too long after adding a new word"""
        assert isinstance(word, str)
        will_be_length = self.len + len(word)
        return will_be_length > MAX_TWEET_LEN

    def set_text(self, text):
        """Set the words array to input text"""
        self.words = [text]

    @property
    def len(self):
        """Length of tweet text"""
        return len(self.str)

    @property
    def is_too_long(self):
        """Does tweet length exceed MAX_TWEET_LEN"""
        return self.len > MAX_TWEET_LEN

    @property
    def str(self):
        """String representation of text"""
        return " ".join(self.words)

    @property
    def twitter_keys(self):
        """Property for the default twitter_keys_from_file file location"""
        return self.twitter_keys_from_file()

    def twitter_keys_from_file(self, keyfile="../keys.txt"):
        """
        Keys for this twitter bot's authorization. Assume the keys file is
        at the location ../keys.txt unless specified otherwise.
        """
        auth_keys = {}

        keyfile_full = os.path.join(os.path.dirname(__file__), keyfile)
        with open(keyfile_full, encoding="utf-8") as keys_fh:
            for row in keys_fh.readlines():
                name, value = row.strip().split("=")
                auth_keys[name] = value

        # Return only the keys for this bot:
        keynames = ["APP_KEY", "APP_SEC", "OAUTH_TOKEN", "OAUTH_TOKEN_SEC"]
        keys = [auth_keys[f"{self.botname}{n}"] for n in keynames]

        return keys

    @property
    def mastodon_access_token(self):
        """Property for the default mastodon_access_token file location"""
        return self.mastodon_access_token_from_file()

    def mastodon_access_token_from_file(self, file="../mastodon_access_tokens.secret"):
        """
        Access tokens for this bot's mastodon authorization. Assume the tokens
        file is at the location ../mastodon_access_tokens.secret unless
        specified otherwise.
        """
        access_token = None
        tokenfile = os.path.join(os.path.dirname(__file__), file)
        with open(tokenfile, encoding="utf-8") as tokens_fh:
            for row in tokens_fh.readlines():
                name, value = row.strip().split()
                if name == self.botname:
                    access_token = value
        return access_token

    def _get_mastodon(self):
        return Mastodon(
            access_token=self.mastodon_access_token,
            api_base_url=MASTODON_API_BASE_URL,
        )

    def publish_mastodon(self, debug=False):
        """Publish to mastodon"""
        if debug:
            print(self.str)
        mastodon = self._get_mastodon()
        mastodon.status_post(self.str)

    def publish_with_image_mastodon(self, image_fn, debug=False):
        """Publish to mastodon with an image"""
        if debug:
            print(self.str)
        mastodon = self._get_mastodon()
        media_dict = mastodon.media_post(mime_type="image/jpeg", media_file=image_fn)
        mastodon.status_post(self.str, media_ids=media_dict)

    def publish(self, debug=False):
        """Publish a tweet"""
        twitter = Twython(*self.twitter_keys)
        if debug:
            print(self.str)
        return twitter.update_status(status=self.str)

    def publish_with_image(self, image_fn, debug=False):
        """Publish a tweet with an image"""
        twitter = Twython(*self.twitter_keys)
        with open(image_fn, "rb") as image:
            response = twitter.upload_media(media=image)
            if debug:
                print(response)
            ids = [response["media_id"]]
            return twitter.update_status(status=self.str, media_ids=ids)

    def download_tweet_text(self, tweet_api_url):
        """
        Get a tweet's text from an API, which should return a JSON object
        with a 'tweet' key
        """
        resp = requests.get(tweet_api_url)
        text = resp.json()["tweet"]
        self.words = [text]

    def __repr__(self):
        return self.str


def get_tweet_filename(filename):
    """Assume the text file is in ../txt/"""
    return os.path.join(os.path.dirname(__file__), f"../txt/{filename}")


def tweetify_text(textfile, use_lines=False):
    """
    Break the input string 'text' into MAX_TWEET_LEN-char-or-less BotTweet
    objects.

    If use_lines is True, make one tweet per line in the file.
    """

    def _tweets_by_line(file_):
        """
        One file line per tweet, truncated to MAX_TWEET_LEN if necessary.
        Returns a list of BotTweet objects.
        """
        tweets = [BotTweet(l) for l in file_.readlines()]
        return tweets

    def _tweets_by_word(file_):
        """
        Make tweets by appending words from file_, staying below MAX_TWEET_LEN
        characters in length.
        Returns a list of BotTweet objects.
        """

        # Fill each tweet until it can't append another word witout getting too
        # long. Then put that tweet into the output list and start a new tweet
        # with the current word.
        #
        tweets = []
        tweet = BotTweet()
        for word in file_.read().split():
            if tweet.can_take_new_word(word):
                tweet.append(word)
            else:
                tweets.append(tweet)
                tweet = BotTweet(word)

        # Append the file's final tweet:
        #
        tweets.append(tweet)
        return tweets

    with open(textfile, encoding="utf-8") as file_:
        tweets = _tweets_by_line(file_) if use_lines else _tweets_by_word(file_)
    return tweets


def get_today_index(num_tweets, then):
    """
    Get today's index into a list that is num_tweets long, starting at 'then'
    """
    now = datetime.datetime.now()
    td_since_start = now - then
    today_index = td_since_start.days % num_tweets
    return today_index


def get_today_tweet(tweets, then):
    """
    Get today's tweet text for the list 'tweets' starting at 'then'
    """
    today_index = get_today_index(len(tweets), then)
    today_tweet = tweets[today_index]
    return today_tweet


def parse_text_and_get_today_tweet(textfile, start_date, use_lines=False):
    """
    Get today's tweet text from a file, starting at 'then'
    """
    tweetfile = get_tweet_filename(textfile)
    tweets = tweetify_text(tweetfile, use_lines)
    return get_today_tweet(tweets, start_date)
