""" Get weather from AccuWeather and email it """

from datetime import datetime as dt
import os
import sys

import requests


# https://github.com/sendgrid/sendgrid-python #pylint: disable=line-too-long
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# https://developer.accuweather.com/user/me/apps

API_PREFIX = "http://dataservice.accuweather.com"
API_FORECAST = f"{API_PREFIX}/forecasts/v1/daily/5day"
API_LOCATION = f"{API_PREFIX}/locations/v1/cities/search"

PRECIP_KEYS = (
    "PrecipitationProbability",
    "PrecipitationIntensity",
    "PrecipitationType",
)

# Template to make a detailed output for today:
#        Today: H 63 Some sun, then clouds
#        Tonight: L 50 Clouds, a little rain late
#
TODAY_TMPL = """
    Today: H {h:.0f} {desc[Day]}
    Tonight: L {l:.0f} {desc[Night]}
"""

# Template to make a summary output for later this week:
#        Fr: H 60 L 47
#        Mostly sunny then clear
#
DAILY_TMPL = """{dow} {h:.0f}-{l:.0f} {desc[Day]} then {desc[night]}"""


def _get_key(name="accuweather"):
    """Get the key for accuweather's API"""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_path = os.path.join(dir_path, "accuweather_key.txt")

    with open(key_path, encoding="UTF-8") as key_file:
        for line in key_file:
            linename, key = line.split()
            if linename == name:
                return key
    return None


def _location_url(name):
    """Get the location URL for AccuWeather"""
    return f"{API_LOCATION}/?q={name}&apikey={_get_key()}"


def _forecast_url(loc_code):
    """Get the forecast URL for AccuWeather"""
    return f"{API_FORECAST}/{loc_code}?apikey={_get_key()}"


def _weather_text(forecasts, line_break="\n    "):
    """Generate a string for the weather report"""
    _text = ""
    for name, forecast in forecasts.items():
        forecast_txt = line_break.join(forecast["forecasts"])
        _text += f"\n\n{name}\n    {forecast['headline']}\n{forecast_txt}"
    return _text


def print_weather(forecasts):
    """Print a report to the terminal"""
    print(_weather_text(forecasts))


def send_email(forecasts):
    """Send the email"""
    line_break = "        <br/>"
    body = _weather_text(forecasts, line_break)

    frm = "kester@gmail.com"
    to = "kester@gmail.com"
    sbj = "AccuWeather Bot forecast"
    message = Mail(from_email=frm, to_emails=to, subject=sbj, html_content=body)

    sendgrid = SendGridAPIClient(_get_key("sendgrid"))
    sendgrid.send(message)


def _desc(forecast):
    """Get the description of the day and precipitation message, if any"""
    msgs = []
    if "HasPrecipitation" in forecast:
        for precip_key in PRECIP_KEYS:
            if precip_key in forecast:
                msgs.append(forecast[precip_key].strip())
    msg = f"{forecast['IconPhrase'].strip()} {' '.join(msgs)}"
    return msg.capitalize().strip()


def parse_forcast_response(data):
    """Get the forecast data out of AccuWeather's json"""
    try:
        headline = data["Headline"]["Text"].strip()
    except KeyError as err:
        print(f"Error: {data['Message']}\n{err}")
        sys.exit(0)

    forecasts = []
    for i, daily in enumerate(data["DailyForecasts"]):
        description = {t: _desc(daily[t]) for t in ("Day", "Night")}
        # convert to lower case for daily template
        description["night"] = description["Night"].lower()

        high = daily["Temperature"]["Maximum"]["Value"]
        low = daily["Temperature"]["Minimum"]["Value"]

        tmpl = DAILY_TMPL if i > 0 else TODAY_TMPL
        dow = dt.fromisoformat(daily["Date"]).strftime("%A")[:2]
        forecast = tmpl.format(dow=dow, desc=description, h=high, l=low)
        forecasts.append(forecast)

    return {"headline": headline, "forecasts": forecasts}


def get_forecast(name):
    """Get the forecast for city {name}"""

    resp = requests.get(_location_url(name))  # pylint: disable=missing-timeout
    resp.raise_for_status()
    loc_code = resp.json()[0]["Key"]

    resp = requests.get(_forecast_url(loc_code))  # pylint: disable=missing-timeout
    resp.raise_for_status()
    forecast = parse_forcast_response(resp.json())
    return forecast


def main():
    """Get weather from AccuWeather and email it"""

    forecasts = {
        "Berkeley, CA": {},
        "Davis, CA": {},
        "Woodland, CA": {},
    }

    try:
        for name in forecasts:
            forecasts[name] = get_forecast(name)

        # send_email(forecasts)
        print_weather(forecasts)
    except requests.HTTPError as err:
        print(f"Error:\nCan't get forecasts:\n     {err}\n    {err.response.text}")


if __name__ == "__main__":
    main()
