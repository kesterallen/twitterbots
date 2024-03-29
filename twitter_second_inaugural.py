
import datetime
import tweetbot_lib

START_DATE = datetime.datetime(2019, 4, 19, 5, 0, 0) # 5AM 18-April-2019

def main():
    if tweetbot_lib.BotTweet.run_recently(seconds=86400):
        return
    tweetbot_lib.MAX_TWEET_LEN = 280
    today_tweet = tweetbot_lib.parse_text_and_get_today_tweet('second_inaugural.txt', START_DATE, use_lines=True)
    today_tweet.publish()

if __name__ == '__main__':
    main()
