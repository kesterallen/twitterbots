"""Module to post to social media for bots. TODO: include bluesky"""

import datetime
import inspect
import os
from pathlib import Path

from mastodon import Mastodon
import requests
from twython import Twython
from twython.exceptions import TwythonAuthError

MAX_TWEET_LEN = 140

MASTODON_API_BASE_URL = "https://botsin.space/"


class BotTweet:
    """Bot tweet module"""

    @classmethod
    def _get_botname(cls):
        frameinfo = inspect.stack()[-1]
        botname = os.path.basename(frameinfo.filename)
        return botname

    @classmethod
    def run_recently(cls, seconds=86400, botname=None) -> bool:
        if botname is None:
            botname = BotTweet._get_botname()
        monitor_file = Path(f"/home/kester/.monitor_{botname}.txt")

        if monitor_file.is_file():
            last_modified = datetime.datetime.fromtimestamp(monitor_file.stat().st_mtime)
            age = datetime.datetime.now() - last_modified
            if age.total_seconds() > seconds:
                # update file
                with monitor_file.open("w") as fh:
                    fh.write(str(datetime.datetime.now()))
                return False
            else:
                return True
        else:
            # create file
            with monitor_file.open("w") as fh:
                fh.write(str(datetime.datetime.now()))
            return False

    # pylint: disable-next=E0601
    def __init__(self, word: str = None, botname: str = None) -> None:
        """Truncate word to MAX_TWEET_LEN if necessary"""
        self.botname = BotTweet._get_botname() if botname is None else botname
        self.words = [] if word is None else [word[:MAX_TWEET_LEN]]

    def pop(self) -> str:
        """Pop a word off of self.words"""
        return self.words.pop()

    def append(self, word: str) -> None:
        """Append 'word' to the self.words list, truncating if necessary"""
        self.words.append(word[:MAX_TWEET_LEN])

    def can_take_new_word(self, word: str) -> bool:
        """Will tweet be under the length limit after adding a new word"""
        return not self.will_be_too_long(word)

    def will_be_too_long(self, word: str) -> bool:
        """Will tweet be too long after adding a new word"""
        assert isinstance(word, str)
        will_be_length = self.len + len(word)
        return will_be_length > MAX_TWEET_LEN

    def set_text(self, text: str) -> None:
        """Set the words array to input text"""
        self.words = [text]

    @property
    def len(self) -> bool:
        """Length of tweet text"""
        return len(self.str)

    @property
    def is_too_long(self) -> bool:
        """Does tweet length exceed MAX_TWEET_LEN"""
        return self.len > MAX_TWEET_LEN

    @property
    def str(self) -> str:
        """String representation of text"""
        return " ".join(self.words)

    @property
    def twitter_keys(self) -> dict:
        """Property for the default twitter_keys_from_file file location"""
        return self.twitter_keys_from_file()

    def twitter_keys_from_file(self, keyfile: str = "../keys.txt") -> dict:
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
    def mastodon_access_token(self) -> str:
        """Property for the default mastodon_access_token file location"""
        return self.mastodon_access_token_from_file()

    def mastodon_access_token_from_file(
        self, file: str = "../mastodon_access_tokens.secret"
    ) -> str:
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

    def _get_mastodon(self) -> Mastodon:
        return Mastodon(
            access_token=self.mastodon_access_token,
            api_base_url=MASTODON_API_BASE_URL,
        )

    def publish(
        self, do_mastodon: bool = True, do_twitter: bool = False) -> None:
        """Publish to twitter and mastodon"""
        if do_twitter:
            twitter = Twython(*self.twitter_keys)
            try:
                twitter.update_status(status=self.str)
            except TwythonAuthError as err:
                print(f"Twython Auth Error: {err}")

        if do_mastodon:
            try:
                mastodon = self._get_mastodon()
                mastodon.status_post(self.str)
            except FileNotFoundError as err:
                print(f"Can't find file: {err}")

    def publish_with_image(
        self,
        image_fn: str,
        do_mastodon: bool = True,
        do_twitter: bool = False,
    ) -> None:
        """Publish to twitter and mastodon with an image"""
        with open(image_fn, "rb") as image:
            if do_twitter:
                try:
                    twitter = Twython(*self.twitter_keys)
                    response = twitter.upload_media(media=image)
                    ids = [response["media_id"]]
                    twitter.update_status(status=self.str, media_ids=ids)
                except TwythonAuthError as err:
                    print(f"Twython Auth Error: {err}")

            if do_mastodon:
                try:
                    mastodon = self._get_mastodon()
                    media_dict = mastodon.media_post(
                        mime_type="image/jpeg", media_file=image_fn
                    )
                    mastodon.status_post(self.str, media_ids=media_dict)
                except FileNotFoundError as err:
                    print(f"Can't find file: {err}")

    def download_tweet_text(self, tweet_api_url: str) -> None:
        """
        Get a tweet's text from an API, which should return a JSON object
        with a 'tweet' key
        """
        resp = requests.get(tweet_api_url, timeout=60)
        text = resp.json()["tweet"]
        self.words = [text]

    def __repr__(self) -> str:
        return self.str


def get_tweet_filename(filename: str) -> str:
    """Assume the text file is in ../txt/"""
    return os.path.join(os.path.dirname(__file__), f"../txt/{filename}")


def tweetify_text(textfile, use_lines: bool = False) -> list[BotTweet]:
    """
    Break the input string 'text' into MAX_TWEET_LEN-char-or-less BotTweet
    objects.

    If use_lines is True, make one tweet per line in the file.
    """

    def _tweets_by_line(file_) -> list[str]:
        """
        One file line per tweet, truncated to MAX_TWEET_LEN if necessary.
        Returns a list of BotTweet objects.
        """
        tweets = [BotTweet(l) for l in file_.readlines()]
        return tweets

    def _tweets_by_word(file_) -> list[str]:
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


def get_today_index(num_tweets: int, start_date: datetime.datetime) -> int:
    """
    Get today's index into a list that is num_tweets long, starting at 'start_date'
    """
    now = datetime.datetime.now()
    td_since_start = now - start_date
    today_index = td_since_start.days % num_tweets
    return today_index


def get_today_tweet(tweets: list[str], start_date: datetime.datetime) -> str:
    """
    Get today's tweet text for the list 'tweets' starting at 'start_date'
    """
    today_index = get_today_index(len(tweets), start_date)
    today_tweet = tweets[today_index]
    return today_tweet


def parse_text_and_get_today_tweet(
    textfile: str, start_date: datetime.datetime, use_lines: bool = False
) -> str:
    """
    Get today's tweet text from a file, starting at 'start_date'
    """
    tweetfile = get_tweet_filename(textfile)
    tweets = tweetify_text(tweetfile, use_lines)
    return get_today_tweet(tweets, start_date)
