
import requests
from tweetbot_lib import BotTweet

tg_json_url = 'http://timeghost-app.appspot.com/tj'

def main():
    tweet_too_long = True
    while tweet_too_long:
        resp = requests.get(tg_json_url)
        text = "%s #timeghost %s" % (
            resp.json()['factoid'], resp.json()['permalink'])
        tweet_too_long = 32 + len(resp.json()['factoid']) > 140

    twitter = BotTweet(text)
    twitter.publish()

if __name__ == '__main__':
    main()
