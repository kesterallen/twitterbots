
import datetime
import os
from tweetbot_lib import (
    BotTweet, tweetify_text, get_today_index, get_tweet_file)

START_DATE = datetime.datetime(2016, 10, 4, 5, 0, 0) # 5AM 4-Oct-2016

def main():
    tweetfile = get_tweet_file('prince_lyrics.txt')
    tweets = tweetify_text(text)
    today_index = get_today_index(len(tweets), START_DATE)
    today_tweet = tweets[today_index]

    today_tweet.publish()

if __name__ == '__main__':
    main()
