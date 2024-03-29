""" Get weather from AccuWeather and email it """

from datetime import datetime as dt
import sys

import requests

# https://github.com/sendgrid/sendgrid-python #pylint: disable=line-too-long
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from python_http_client.exceptions import UnauthorizedError

# https://developer.accuweather.com/user/me/apps

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
<br/>Today: H {h:.0f} {desc[Day]}
<br/>Tonight: L {l:.0f} {desc[Night]}
<br/>
"""

# Template to make a summary output for later this week:
#        Fr: H 60 L 47
#        Mostly sunny then clear
#
DAILY_TMPL = """{dow} {h:.0f}-{l:.0f} {desc[Day]} then {desc[night]}"""


def get_url():
    """Get the URL with app key for AccuWeather"""
    with open("accuweather_key.txt", encoding="UTF-8") as key_file:
        key = key_file.readline().split(" ")[1].strip()

    loc = "39625_PC" # berkeley
    url = f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{loc}?apikey={key}"
    return url


def send_email(headline, forecasts):
    """Send the email"""
    line_break = "        <br/>"
    forecast_txt = line_break.join(forecasts)
    body = f"\n{headline}{line_break}\n{forecast_txt}{line_break}"

    from_email = "kester@gmail.com"
    to_email = "kester@gmail.com"
    subject = f"AccuWeather Bot: {headline}"
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=body,
    )

    with open("accuweather_key.txt", encoding="UTF-8") as key_file:
        _ = key_file.readline()
        sendgrid_key = key_file.readline().split(" ")[1].strip()
    sendgrid = SendGridAPIClient(sendgrid_key)
    try:
        _ = sendgrid.send(message)  # hide 'response' into '_' for pylint
    except UnauthorizedError as err:
        print(f"Sendgrid error {err}, printing report")
        print(forecast_txt.replace(line_break, ""))


def _desc(forecast):
    """Get the description of the day and precipitation message, if any"""
    msgs = []
    if "HasPrecipitation" in forecast:
        for precip_key in PRECIP_KEYS:
            if precip_key in forecast:
                msgs.append(forecast[precip_key].strip())
    msg = f"{forecast['IconPhrase'].strip()} {' '.join(msgs)}"
    return msg.capitalize().strip()

def parse_data(data):
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

    return headline, forecasts


def main():
    """Get weather from AccuWeather and email it"""
    resp = requests.get(get_url())
    data = resp.json()

    headline, forecasts = parse_data(data)
    send_email(headline, forecasts)


if __name__ == "__main__":
    main()
