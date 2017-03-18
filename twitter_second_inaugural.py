
import datetime
import os
from tweetbot_lib import BotTweet, tweetify_text, get_today_index, get_keys

START_DATE = datetime.datetime(2016, 11, 28, 5, 0, 0) # 5AM 28-Nov-2016
LYRICS_FILE = 'txt/second_inaugural.txt'
KEY_FILE = 'keys.txt'

def main():
    keys = get_keys(KEY_FILE, __file__)
    tweets = tweetify_text(LYRICS_FILE)
    today_index = get_today_index(len(tweets), START_DATE)
    today_tweet = tweets[today_index]
    today_tweet.publish(*keys)

if __name__ == '__main__':
    main()
