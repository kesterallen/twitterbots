
from attrdict import AttrDict
import math
import numpy as np
import os
from PIL import Image, ImageOps
import random
from scipy import optimize
import sys
from tweetbot_lib import BotTweet
import urllib

DEBUG = False
IMAGE_FN = "tmpplanet.jpg"

PLANETS = AttrDict({
    'Venus': AttrDict({ 
        'map': '/maps/venus/venus_simp_cyl.map',
        'layers': 'MAGELLAN',
        'botname': 'venusbot',
        'lat_box_side_degrees': (0.1, 3.0),
    }),
    'Mercury': AttrDict({
        'map': '/maps/mercury/mercury_simp_cyl.map',
        'layers':'MESSENGER_Color',
        'botname': 'mercurybot',
        'lat_box_side_degrees': (1.0, 20.0),
    })
})

# Thanks to Trent Hare of the USGS for this service:
#
IMG_URL_TMPL = "".join([
    'https://planetarymaps.usgs.gov/cgi-bin/mapserv?',
        'map={0.map}&',
        'SERVICE=WMS&',
        'VERSION=1.1.1&',
        'SRS=EPSG:4326&',
        'STYLES=&',
        'REQUEST=GetMap&',
        'FORMAT=image%2Fjpeg&',
        'LAYERS={0.layers}&',
        'BBOX={1.str}&',
        'WIDTH={2}&',
        'HEIGHT={3}',
])

class BoundingBox(object):
    def __init__(self, lng, lat, lat_box_side, aspect_ratio):
        self.lng = lng
        self.lat = lat

        # Adjust the lng (horizontal) size of the box by aspect ratio and
        # the latitude (so high-latitude images look right):
        lat_rad = lat * math.pi / 180.0
        lng_box_side = lat_box_side * aspect_ratio / math.cos(abs(lat_rad)) 

        self.lng_end = lng + lng_box_side
        self.lat_end = lat + lat_box_side

    @property
    def box_width_km(self):
        # TODO: this is actually the height
        return 105.6 * (self.lat_end - self.lat)

    @property
    def is_bad(self):
        return self.lng_end >= 360.0 or abs(self.lat_end) >= 90.0

    @property
    def str(self):
        return "{0.lng},{0.lat},{0.lng_end},{0.lat_end}".format(self)

    @property
    def pretty_str(self):
        return "latitude: %.1f longitude: %.1f, %.1f km wide" % (
            self.lat, self.lng, self.box_width_km)


def get_bounding_box(lat_box_side, aspect_ratio):
    """Get a bounding box that is lat_box_side high and within bounds."""
    is_bad_box = True
    while is_bad_box:
        # Math from http://mathworld.wolfram.com/SpherePointPicking.html
        rand_u = random.random()
        rand_v = random.random()
        lng = 360.0 * rand_u # Range: [0.0, 360.0]
        lat = math.acos(2.0 * rand_v - 1) * 180.0 / math.pi - 90.0 # Range: [-90.0, 90.0]

        box = BoundingBox(lng, lat, lat_box_side, aspect_ratio)
        is_bad_box = box.is_bad

    return box

def _gauss(x, *p):
    """ Define model function to be used to fit to the data. """
    A, mu, sigma = p
    return A * np.exp(-(x-mu)**2/(2.0*sigma**2))

def _ignore(hist, offset=10, width=3.0):
    """ 
    Generate an ignore range that excludes everything based on a gaussian fit
    to hist[offset:] (ignore first offset bins). Default ignore range is
    everything outside +/- 3 std from the center of the gaussian fit.
    """

    # p0 is the initial guess for the fitting coefficients (A, mu, & sigma)
    p_max = max(hist[offset:]) # value of biggest peak in hist, excluding 0:offset
    p_ctr = hist.index(p_max) # the index location of that value
    p_std = 20.0 # initial guess, ~10% of hist width
    p0 = [p_max, p_ctr, p_std]

    # Perform the fit, and get the fit coefficients:
    coeff, var_matrix = optimize.curve_fit(_gauss, range(len(hist)), hist, p0=p0)

    # Get the left and right edges of +/- 3 std dev from the fit center:
    data_start = int(coeff[1] - width*coeff[2])
    data_end = int(coeff[1] + width*coeff[2])

    # If the fit is weird, revert to very conservative values.
    if data_start < 0 or data_start > 255:
        data_start = 0
    if data_end < 0 or data_end > 255:
        data_end = 255
    if data_end <= data_start:
        data_start = 0
        data_end = 255

    ignore = range(0,data_start) + range(data_end,255)

    return ignore

def get_random_planet_image(planet, width, height, lat_box_side, max_pct_black=0.5):
    """Get a subimage without too many black pixels"""

    planet_data = PLANETS[planet]

    # TODO: this should probably be a stringio
    aspect_ratio = float(width) / float(height)
    image_too_dark = True
    while image_too_dark:
        box = get_bounding_box(lat_box_side, aspect_ratio)
        url = IMG_URL_TMPL.format(planet_data, box, width, height)
        urllib.urlretrieve(url, IMAGE_FN)

        image = Image.open(IMAGE_FN).convert('L')
        hist = image.histogram()

        num_black = hist[0]
        pct_black = float(num_black) / float(sum(image.histogram()))
        image_too_dark = pct_black > max_pct_black

    ignore = _ignore(hist)
    image = ImageOps.autocontrast(image, ignore=ignore)
    image.save(IMAGE_FN)

    if DEBUG:
        print box.pretty_str
        print url
        print "http://surlyfritter.appspot.com/globe?%s,%s,4" % (box.lat, box.lng)

    return box, url

def main():
    planet_name = sys.argv[1]
    assert planet_name in PLANETS

    width = 1920
    height = 1080
    lat_box_side = random.uniform(*PLANETS[planet_name].lat_box_side_degrees)

    box, url = get_random_planet_image(planet_name, width, height, lat_box_side)

    if DEBUG:
        import ipdb; ipdb.set_trace()
    text = "%s, %s" % (box.pretty_str, url)
    # TODO: add bot_filename arg here to distinguish keys
    twitter = BotTweet(word=text, bot_filename=PLANETS[planet_name]['botname'])

    if not DEBUG:
        twitter.publish_with_image(IMAGE_FN)

    os.remove(IMAGE_FN)

if __name__ == '__main__':
    main()

# For Venus:
# http://surlyfritter.appspot.com/globe?45,-65,4 
# and 
# https://planetarymaps.usgs.gov/cgi-bin/mapserv?map=/maps/venus/venus_simp_cyl.map&SERVICE=WMS&VERSION=1.1.1&SRS=EPSG:4326&STYLES=&REQUEST=GetMap&FORMAT=image%2Fjpeg&LAYERS=MAGELLAN&BBOX=90,-45,215.707872211,5&WIDTH=1920&HEIGHT=1080
# match!
