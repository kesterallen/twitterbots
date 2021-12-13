"""
Module to make images and descriptions of planets from the USGS planetary map
server's CGI service.
"""
from math import acos, cos, pi
import random
import sys
import urllib

from attrdict import AttrDict
import numpy as np
from PIL import Image, ImageOps
from scipy import optimize
from tweetbot_lib import BotTweet

DEBUG = False
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080

PLANETS = AttrDict(
    {
        "Venus": AttrDict(
            {
                "botname": "venusbot",
                "map": "/maps/venus/venus_simp_cyl.map",
                "layers": "MAGELLAN",
                "lat_box_side_degrees": (0.1, 3.0),
                "km_per_lat_deg": 105.6,
            }
        ),
        "Mercury": AttrDict(
            {
                "botname": "mercurybot",
                "map": "/maps/mercury/mercury_simp_cyl.map",
                "layers": "MESSENGER_Color",
                "lat_box_side_degrees": (1.0, 20.0),
                "km_per_lat_deg": 42.58,
            }
        ),
    }
)


class BoundingBox:
    """A bounding box in latitude/longitude with the correct aspect ratio"""

    def __init__(self, lat_box_side, aspect_ratio, km_per_lat_deg, loc=None):
        """
        Create a new box, adjusting the lng (horizontal) size of the box by
        aspect ratio and the latitude (so high-latitude images look right).
        If specified, loc must have .lat and .lng attributes
        """
        assert loc is None or ("lng" in loc and "lat" in loc)

        self.lat = BoundingBox._rand_lat() if loc is None else loc.lat
        self.lat_end = self.lat + lat_box_side

        self.lng = BoundingBox._rand_lng() if loc is None else loc.lng
        lng_box_side = lat_box_side * aspect_ratio / cos(abs(self.lat * pi / 180.0))
        self.lng_end = self.lng + lng_box_side

        self.km_per_lat_deg = km_per_lat_deg

    @classmethod
    def _rand_lng(cls):
        """
        lng range: [0.0, 360.0]
        Math source: http://mathworld.wolfram.com/SpherePointPicking.html
        """
        rand_u = random.random()
        return 360.0 * rand_u

    @classmethod
    def _rand_lat(cls):
        """
        lat range: [-90.0, 90.0]
        Math source: http://mathworld.wolfram.com/SpherePointPicking.html
        """
        rand_v = random.random()
        return acos(2.0 * rand_v - 1) * 180.0 / pi - 90.0

    def __bool__(self):
        return not self.is_out_of_range

    @classmethod
    def get_rand(cls, lat_box_side, aspect_ratio, km_per_lat_deg, max_tries=100):
        """
        Get a bounding box that is lat_box_side high and within bounds (all 4
        corners in the lat range [-90, 90] and the lng range [0, 360]).
        Bails out after max_tries if the geometry is pathological (gigantic
        lat_box_side?).

        Math source: http://mathworld.wolfram.com/SpherePointPicking.html

        """
        tries = 0
        box = BoundingBox(lat_box_side, aspect_ratio, km_per_lat_deg)
        while box.is_out_of_range and tries < max_tries:
            box = BoundingBox(lat_box_side, aspect_ratio, km_per_lat_deg)
            tries += 1

        return box

    @property
    def box_height_km(self):
        """The box's latitude measure"""
        return self.km_per_lat_deg * (self.lat_end - self.lat)

    @property
    def is_out_of_range(self):
        """Are the end points for latitude or longitude incorrect"""
        return self.lng_end >= 360.0 or abs(self.lat_end) >= 90.0

    @property
    def str(self):
        """String representation"""
        return f"{self.lng},{self.lat},{self.lng_end},{self.lat_end}"

    @property
    def pretty_str(self):
        """More verbose string representation"""
        return (
            f"latitude: {self.lat:.1f} longitude: {self.lng:.1f}, "
            f"{self.box_height_km:.1f} km wide"
        )

    @property
    def lat_gmap(self):
        """Google Maps latitude center"""
        return 0.5 * (self.lat + self.lat_end)

    @property
    def lng_gmap(self):
        """Google Maps longitude runs from -180 to 180, not 0 to 360"""
        return -180.0 + 0.5 * (self.lng + self.lng_end)


def _gauss(x, *p):
    """Define model function to be used to fit to the data"""
    # pylint: disable=invalid-name
    A, mu, sigma = p
    return A * np.exp(-((x - mu) ** 2) / (2.0 * sigma ** 2))


def _ignore(hist, offset=10, width=3.0):
    """
    Generate an ignore range that excludes everything based on a gaussian fit
    to hist[offset:] (ignore first offset bins). Default ignore range is
    everything outside +/- 3 std from the center of the gaussian fit.
    """
    # pylint: disable=unused-variable,unbalanced-tuple-unpacking

    # p0 is the initial guess for the fitting coefficients (A, mu, & sigma)
    p_max = max(hist[offset:])  # value of biggest peak in hist, excluding 0:offset
    p_ctr = hist.index(p_max)  # the index location of that value
    p_std = 20.0  # initial guess, ~10% of hist width
    params_initial = [p_max, p_ctr, p_std]

    # Perform the fit, and get the fit coefficients:
    xdata = list(range(len(hist)))
    coeff, var_matrix = optimize.curve_fit(_gauss, xdata, hist, params_initial)

    # Get the left and right edges of +/- 3 std dev from the fit center:
    data_start = int(coeff[1] - width * coeff[2])
    data_end = int(coeff[1] + width * coeff[2])

    # If the fit is out of bounds, revert to very conservative values:
    if data_start < 0 or data_start > 255:
        data_start = 0
    if data_end < 0 or data_end > 255:
        data_end = 255
    if data_end <= data_start:
        data_start = 0
        data_end = 255

    ignore = list(range(0, data_start)) + list(range(data_end, 255))
    if DEBUG:
        print(ignore)

    return ignore


def _usgs_url(planet, box, width, height):
    """Thanks to Trent Hare of the USGS for this service"""
    return (
        "https://planetarymaps.usgs.gov/cgi-bin/mapserv?"
        "SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326&STYLES=&REQUEST=GetMap&"
        "FORMAT=image%2Fjpeg&"
        f"LAYERS={planet.layers}&BBOX={box.str}&"
        f"WIDTH={width}&HEIGHT={height}&map={planet.map_}"
    )


def _get_image(lat_box_side, planet, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """Get a subimage to check for black pixel amount"""
    aspect_ratio = float(width) / float(height)
    box = BoundingBox.get_rand(lat_box_side, aspect_ratio, planet.km_per_lat_deg)
    url = _usgs_url(planet, box, width, height)
    tmp_fn, headers = urllib.request.urlretrieve(url)  # pylint: disable=unused-variable
    image = Image.open(tmp_fn).convert("L")
    return (box, url, tmp_fn, image)


def random_planet_image(planet, max_pct_black=0.5):
    """Get a subimage without too many black pixels"""

    lat_box_side = random.uniform(*planet.lat_box_side_degrees)

    image_too_dark = True
    while image_too_dark:
        box, url, tmp_fn, image = _get_image(lat_box_side, planet)
        hist = image.histogram()

        num_black = hist[0]
        pct_black = float(num_black) / float(sum(image.histogram()))
        image_too_dark = pct_black > max_pct_black

    ignore = _ignore(hist)
    image = ImageOps.autocontrast(image, ignore=ignore)
    image_fn = f"{tmp_fn}.jpg"
    image.save(image_fn)

    if DEBUG:
        print(box.pretty_str, url)

    return box, url, image_fn


def main():
    """
    Generate and publish a planet image
    """
    planet_name = sys.argv[1]
    assert planet_name in PLANETS
    planet = PLANETS[planet_name]

    box, url, image_fn = random_planet_image(planet)
    if DEBUG:
        print(box.pretty_str, url)

    tweet_text = f"{planet_name}, {box.pretty_str}, {url}"
    twitter = BotTweet(word=tweet_text, botname=planet.botname)

    if not DEBUG:
        twitter.publish_with_image(image_fn)


if __name__ == "__main__":
    main()

# For Venus:
# https://planetarymaps.usgs.gov/cgi-bin/mapserv?map=/maps/venus/venus_simp_cyl.map&SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326&STYLES=&REQUEST=GetMap&FORMAT=image%2Fjpeg&LAYERS=MAGELLAN&BBOX=90,-45,215.707872211,5&WIDTH=1920&HEIGHT=1080
# match!
