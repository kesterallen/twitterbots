
import datetime
from tweetbot_lib import parse_text_and_get_today_tweet

START_DATE = datetime.datetime(2016, 11, 28, 5, 0, 0) # 5AM 28-Nov-2016

def main():
    today_tweet = parse_text_and_get_today_tweet('gettysburg.txt', START_DATE)
    today_tweet.publish()
    today_tweet.publish_mastodon()

if __name__ == '__main__':
    main()
