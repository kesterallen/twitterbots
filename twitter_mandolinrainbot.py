
import datetime
from tweetbot_lib import parse_text_and_get_today_tweet, BotTweet

START_DATE = datetime.datetime(2018, 5, 25, 5, 0, 0) # 5AM 25-May-2018

def main():
    if BotTweet.run_recently(seconds=86400):
        return
    today_tweet = parse_text_and_get_today_tweet('mandolin_rain.txt', START_DATE, use_lines=True)
    today_tweet.publish()

if __name__ == '__main__':
    main()
