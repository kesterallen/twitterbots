
import datetime
import os
from tweetbot_lib import (
    BotTweet, tweetify_text, get_today_index, get_keys, get_tweet_file)

START_DATE = datetime.datetime(2016, 10, 17, 5, 0, 0) # 5AM 17-Oct-2016
KEY_FILE = 'keys.txt'

def main():
    tweetfile = get_tweet_file('guthrie_lyrics.txt')
    tweets = tweetify_text(text)
    today_index = get_today_index(len(tweets), START_DATE)
    today_tweet = tweets[today_index]

    keys = get_keys(__file__)
    today_tweet.publish(*keys)

if __name__ == '__main__':
    main()
