""" Set the featured plaque for the day and tweet about it """
import requests

from tweetbot_lib import BotTweet

TWEET_URL = "https://readtheplaque.com/tweet"
FEATURED_GEOJSON_URL = "https://readtheplaque.com/featured/geojson"

def main():
    """
    Set the featured plaque for the day and tweet it, also send a tweet to the
    submitter if they are specified in the plaque description
    """
    twitter = BotTweet()
    twitter.download_tweet_text(TWEET_URL)
    twitter.publish()

    # Send a tweet to the submitter, if specified
    resp = requests.get(FEATURED_GEOJSON_URL)
    submitter_tweet_text = resp.json()["submitter_tweet"]
    if submitter_tweet_text is not None:
        twitter.words = [submitter_tweet_text]
        twitter.publish()


if __name__ == '__main__':
    main()
