import datetime
from blueskybot_lib import post_for_today

if __name__ == "__main__":
    start_date = datetime.datetime(2026, 11, 13, 11, 11, 11)
    post_for_today("mandolinrain", "mandolin_rain.txt", start_date)
