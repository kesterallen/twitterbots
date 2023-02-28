
import datetime
from tweetbot_lib import parse_text_and_get_today_tweet

START_DATE = datetime.datetime(2018, 5, 25, 5, 0, 0) # 5AM 25-May-2018

def main():
    today_tweet = parse_text_and_get_today_tweet('mandolin_rain.txt', START_DATE, use_lines=True)
    today_tweet.publish()
    # TODO today_tweet.publish_mastodon("mandolinrainbot")

if __name__ == '__main__':
    main()
