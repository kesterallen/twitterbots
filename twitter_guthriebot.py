
import datetime
import os
from tweetbot_lib import parse_text_and_get_today_tweet

START_DATE = datetime.datetime(2016, 10, 17, 5, 0, 0) # 5AM 17-Oct-2016

def main():
    today_tweet = parse_text_and_get_today_tweet('guthrie_lyrics.txt', START_DATE)
    today_tweet.publish()

if __name__ == '__main__':
    main()
