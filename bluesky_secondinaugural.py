import datetime
from blueskybot_lib import post_for_today

if __name__ == "__main__":
    start_date = datetime.datetime(2026, 11, 11, 11, 11, 11)  # corduroy day '26
    post_for_today("secondinaugural", "second_inaugural.txt", start_date)
