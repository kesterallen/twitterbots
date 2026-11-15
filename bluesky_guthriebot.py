import datetime
from blueskybot_lib import parse_text_and_get_today_post, BotPost

START_DATE = datetime.datetime(2026, 11, 13, 11, 11, 11)


def main():
    if BotPost.run_recently(seconds=86400, botname="guthriebot"):
        return

    today_post = parse_text_and_get_today_post("guthrie_lyrics.txt", START_DATE)
    today_post.publish()


if __name__ == "__main__":
    main()
