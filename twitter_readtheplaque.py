
import requests
from tweetbot_lib import BotTweet

set_featured_url = 'http://readtheplaque.com/jp'

def main():
    resp = requests.get(set_featured_url)
    text = "'%s' Always #readtheplaque http://readtheplaque.com/plaque/%s" % (
        resp.json()['title'], resp.json()['title_url'])

    twitter = BotTweet(text)
    twitter.publish()

if __name__ == '__main__':
    main()
