
import datetime
from tweetbot_lib import parse_text_and_get_today_tweet, BotTweet

START_DATE = datetime.datetime(2016, 11, 28, 5, 0, 0) # 5AM 28-Nov-2016

def main():
    if BotTweet.run_recently(seconds=86400):
        return
    today_tweet = parse_text_and_get_today_tweet('gettysburg.txt', START_DATE)
    today_tweet.publish()

if __name__ == '__main__':
    main()
