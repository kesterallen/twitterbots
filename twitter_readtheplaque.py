""" Set the featured plaque for the day and tweet about it """

import requests
from tweetbot_lib import BotTweet

PREFIX = "https://readtheplaque.com/"
SUFFIXES = {
    "RAND": "featured/random",
    "FLUSH": "flush",
    "TWEET": "tweet",
    "GEOJSON": "featured/geojson",
}
URLS = {k: f"{PREFIX}{v}" for k, v in SUFFIXES.items()}


def main():
    """
    1) Set the featured plaque for the day,
    2) Publish a tweet about it,
    3) send a tweet to the plaque's submitter (if they are specified in the plaque description)
    """
    if BotTweet.run_recently(seconds=86400):
        return

    resp = requests.get(URLS["RAND"])
    requests.get(URLS["FLUSH"])
    resp_json = resp.json()

    twitter = BotTweet(resp_json["tweet"])
    twitter.publish()

    # Send a tweet to the submitter (if the plaque's geojson specifies a
    # submitter, see Models.py:Plaque:tweet_to_plaque_submitter in
    # https://github.com/kesterallen/read-the-plaque)
    #
    if submitter_tweet := resp_json["submitter_tweet"]:
        twitter.set_text(submitter_tweet)
        twitter.publish()

if __name__ == "__main__":
    main()
