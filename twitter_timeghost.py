
from tweetbot_lib import BotTweet

tweet_url = 'http://timeg.host/tweet' #'https://timeghost-app.appspot.com/tweet'

def main():
    if BotTweet.run_recently(seconds=86400):
        return
    twitter = BotTweet()
    twitter.download_tweet_text(tweet_url)
    twitter.publish()

if __name__ == '__main__':
    main()
