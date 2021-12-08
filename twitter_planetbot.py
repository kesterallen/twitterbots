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

PLANETS = AttrDict({
    'Venus': AttrDict({
        'map': '/maps/venus/venus_simp_cyl.map',
        'layers': 'MAGELLAN',
        'botname': 'venusbot',
        'lat_box_side_degrees': (0.1, 3.0),
        'km_per_lat_deg': 105.6,
    }),
    'Mercury': AttrDict({
        'map': '/maps/mercury/mercury_simp_cyl.map',
        'layers':'MESSENGER_Color',
        'botname': 'mercurybot',
        'lat_box_side_degrees': (1.0, 20.0),
        'km_per_lat_deg': 42.58,
    })
})

def usgs_url(planet_data, box, width, height):
    """ Thanks to Trent Hare of the USGS for this service """
    return (
        "https://planetarymaps.usgs.gov/cgi-bin/mapserv?"
        "SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326&STYLES=&REQUEST=GetMap&"
        "FORMAT=image%2Fjpeg&"
        f"LAYERS={planet_data.layers}&BBOX={box.str}&"
        f"WIDTH={width}&HEIGHT={height}&map={planet_data.map}"
    )

class BoundingBox:
    """A bounding box in latitude/longitude with the correct aspect ratio"""
    def __init__(self, lng_lat_side, aspect_ratio, km_per_lat_deg):
        """Create a new box"""
        self.lng = lng_lat_side.lng
        self.lat = lng_lat_side.lat

        # Adjust the lng (horizontal) size of the box by aspect ratio and
        # the latitude (so high-latitude images look right):
        lat_rad = lng_lat_side.lat * pi / 180.0
        lng_box_side = lng_lat_side.side * aspect_ratio / cos(abs(lat_rad))

        self.lng_end = lng_lat_side.lng + lng_box_side
        self.lat_end = lng_lat_side.lat + lng_lat_side.side

        self.km_per_lat_deg = km_per_lat_deg

    @property
    def box_height_km(self):
        """The box's latitude measure"""
        return self.km_per_lat_deg * (self.lat_end - self.lat)

    @property
    def is_bad(self):
        """Are the end points for latitude or longitude incorrect"""
        return self.lng_end >= 360.0 or abs(self.lat_end) >= 90.0

    @property
    def str(self):
        """String representation"""
        return f"{self.lng},{self.lat},{self.lng_end},{self.lat_end}"

    @property
    def pretty_str(self):
        """More verbose string representation"""
        return(f"latitude: {self.lat:.1f} longitude: {self.lng:.1f}, "
            f"{self.box_height_km:.1f} km wide")

    @property
    def lat_gmap(self):
        """Google Maps latitude center"""
        return 0.5 * (self.lat + self.lat_end)

    @property
    def lng_gmap(self):
        """Google Maps longitude runs from -180 to 180, not 0 to 360"""
        return -180.0 + 0.5 * (self.lng + self.lng_end)


def get_bounding_box(lat_box_side, aspect_ratio, km_per_lat_deg):
    """Get a bounding box that is lat_box_side high and within bounds"""
    is_bad_box = True
    while is_bad_box:
        # Math from http://mathworld.wolfram.com/SpherePointPicking.html
        rand_u = random.random()
        rand_v = random.random()
        # lng range: [0.0, 360.0]
        # lat range: [-90.0, 90.0]
        lng = 360.0 * rand_u
        lat = acos(2.0 * rand_v - 1) * 180.0 / pi - 90.0
        lng_lat_side = AttrDict({'lng': lng, 'lat': lat, 'side': lat_box_side})

        box = BoundingBox(lng_lat_side, aspect_ratio, km_per_lat_deg)
        is_bad_box = box.is_bad

    return box

def _gauss(x, *p):
    """Define model function to be used to fit to the data"""
    # pylint: disable=invalid-name
    A, mu, sigma = p
    return A * np.exp(-(x-mu)**2/(2.0*sigma**2))

def _ignore(hist, offset=10, width=3.0):
    """
    Generate an ignore range that excludes everything based on a gaussian fit
    to hist[offset:] (ignore first offset bins). Default ignore range is
    everything outside +/- 3 std from the center of the gaussian fit.
    """
    #pylint: disable=unused-variable,unbalanced-tuple-unpacking

    # p0 is the initial guess for the fitting coefficients (A, mu, & sigma)
    p_max = max(hist[offset:]) # value of biggest peak in hist, excluding 0:offset
    p_ctr = hist.index(p_max) # the index location of that value
    p_std = 20.0 # initial guess, ~10% of hist width
    params_initial = [p_max, p_ctr, p_std]

    # Perform the fit, and get the fit coefficients:
    xdata = list(range(len(hist)))
    coeff, var_matrix = optimize.curve_fit(_gauss, xdata, hist, params_initial)

    # Get the left and right edges of +/- 3 std dev from the fit center:
    data_start = int(coeff[1] - width*coeff[2])
    data_end = int(coeff[1] + width*coeff[2])

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

def _get_image(lat_box_side, width, height, planet_data):
    """Get a subimage to check for black pixel amount"""
    aspect_ratio = float(width) / float(height)
    box = get_bounding_box(lat_box_side, aspect_ratio, planet_data.km_per_lat_deg)
    url = usgs_url(planet_data, box, width, height)
    tmp_fn, headers = urllib.request.urlretrieve(url) #pylint: disable=unused-variable
    image = Image.open(tmp_fn).convert('L')
    return(box, url, tmp_fn, image)

def get_random_planet_image(planet_data, width, height, lat_box_side, max_pct_black=0.5):
    """Get a subimage without too many black pixels"""

    image_too_dark = True
    while image_too_dark:
        box, url, tmp_fn, image = _get_image(lat_box_side, width, height, planet_data)
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

    width = 1920
    height = 1080
    lat_box_side = random.uniform(*PLANETS[planet_name].lat_box_side_degrees)

    box, url, image_fn = get_random_planet_image(PLANETS[planet_name], width, height, lat_box_side)

    if DEBUG:
        print(box.pretty_str, url)

    tweet_text = f"{planet_name}, {box.pretty_str}, {url}"
    twitter = BotTweet(word=tweet_text, botname=PLANETS[planet_name]['botname'])

    if not DEBUG:
        twitter.publish_with_image(image_fn)

if __name__ == '__main__':
    main()

# For Venus:
# https://planetarymaps.usgs.gov/cgi-bin/mapserv?map=/maps/venus/venus_simp_cyl.map&SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326&STYLES=&REQUEST=GetMap&FORMAT=image%2Fjpeg&LAYERS=MAGELLAN&BBOX=90,-45,215.707872211,5&WIDTH=1920&HEIGHT=1080
# match!
