import datetime
from blueskybot_lib import parse_text_and_get_today_post, BotPost

START_DATE = datetime.datetime(2026, 11, 11, 11, 11, 11)  # corduroy day '26


def main():
    if BotPost.run_recently(seconds=86400, botname="bluesky_gettysburg"):
        return

    today_post = parse_text_and_get_today_post("gettysburg.txt", START_DATE)
    today_post.publish()


if __name__ == "__main__":
    main()
