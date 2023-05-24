
from tweetbot_lib import BotTweet

tweet_url = 'http://timeg.host/tweet' #'https://timeghost-app.appspot.com/tweet'

def main():
    twitter = BotTweet()
    twitter.download_tweet_text(tweet_url)
    twitter.publish()
    #twitter.publish_mastodon()

if __name__ == '__main__':
    main()
