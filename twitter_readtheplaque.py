""" Set the featured plaque for the day and tweet about it """
import requests
from tweetbot_lib import BotTweet

URL_PREF = "https://readtheplaque.com/"
URLS = {
    "RAND": URL_PREF + "featured/random",
    "TWEET": URL_PREF + "tweet",
    "GEOJSON": URL_PREF + "featured/geojson",
}


def main():
    """
    1) Set the featured plaque for the day,
    2) Publish a tweet about it,
    3) send a tweet to the plaque's submitter (if they are specified in the plaque description)
    """
    resp = requests.get(URLS["RAND"])
    resp_json = resp.json()

    twitter = BotTweet(resp_json["tweet"])
    twitter.publish()

    # Send a tweet to the submitter (if the plaque's geojson specifies a
    # submitter, see Models.py:Plaque:tweet_to_plaque_submitter in
    # https://github.com/kesterallen/read-the-plaque)
    #
    if submitter_tweet_text := resp_json["submitter_tweet"]:
        twitter = BotTweet(submitter_tweet_text)
        twitter.publish()


if __name__ == "__main__":
    main()
