
import attrdict
import math
import numpy as np
import os
from PIL import Image, ImageOps
import random
from scipy import optimize
from tweetbot_lib import BotTweet
import urllib

# Thanks to Trent Hare of the USGS for this service:
#
IMG_TMPL = "".join([
    'https://planetarymaps.usgs.gov/cgi-bin/mapserv?',
        'map=/maps/venus/venus_simp_cyl.map&',
        'SERVICE=WMS&',
        'VERSION=1.1.1&',
        'SRS=EPSG:4326&',
        'STYLES=&',
        'REQUEST=GetMap&',
        'FORMAT=image%%2Fjpeg&',
        'LAYERS=MAGELLAN&',
        'BBOX=%s&',
        'WIDTH=%s&',
        'HEIGHT=%s',
])

def get_bounding_box(lat_box_side, aspect_ratio):
    """Get a bounding box that is lat_box_side high and within bounds."""
    is_bad_box = True
    while is_bad_box:
        # Math from http://mathworld.wolfram.com/SpherePointPicking.html
        rand_u = random.random()
        rand_v = random.random()
        lng = 360.0 * rand_u # Range: [0.0, 360.0]
        lat = math.acos(2.0 * rand_v - 1) * 180.0 / math.pi - 90.0 # Range: [-90.0, 90.0]

        # Convert latitude to radans for the cos operation
        lat_rad = lat * math.pi / 180.0
        lng_box_side = lat_box_side * math.cos(abs(lat_rad)) * aspect_ratio

        lng_end = lng + lng_box_side
        lat_end = lat + lat_box_side

        box_width_km = 105.6 * lat_box_side

        is_bad_box = lng_end >= 360.0 or abs(lat_end) >= 90.0

    return attrdict.AttrDict({
        'lng': lng,
        'lat': lat,
        'lng_end': lng_end,
        'lat_end': lat_end,
        'box_width_km': box_width_km
    })

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
    p_max = max(hist[offset:])
    p_ctr = hist.index(p_max)
    p_std = 20.0
    p0 = [p_max, p_ctr, p_std]
    coeff, var_matrix = optimize.curve_fit(_gauss, range(len(hist)), hist, p0=p0)

    data_start = int(coeff[1] - width*coeff[2])

    if data_start < 0 or data_start > 255:
        data_start = 0
    data_end = int(coeff[1] + width*coeff[2])
    if data_end < 0 or data_end > 255:
        data_end = 255
    if data_end <= data_start:
        data_start = 0
        data_end = 255

    ignore = range(0,data_start) + range(data_end,255)

    return ignore


def get_random_venus_image(width, height, lat_box_side, max_pct_black=0.5):
    """Get a subimage without too many black pixels"""

    # TODO: this should probably be a stringio
    aspect_ratio = float(width) / float(height)
    image_fn = "tmpvenus.jpg"
    image_too_dark = True
    while image_too_dark:
        box = get_bounding_box(lat_box_side, aspect_ratio)
        str_box = "%s,%s,%s,%s" % (box.lng, box.lat, box.lng_end, box.lat_end)
        url = IMG_TMPL % (str_box, width, height)
        urllib.urlretrieve(url, image_fn)

        image = Image.open(image_fn).convert('L')
        hist = image.histogram()

        num_black = hist[0]
        pct_black = float(num_black) / float(sum(image.histogram()))
        image_too_dark = pct_black > max_pct_black

    image.save("tmpraw.jpg")
    ignore = _ignore(hist)
    image = ImageOps.autocontrast(image, ignore=ignore)
    image.save(image_fn)

    return box, url, image_fn

def main():
    width = 1920
    height = 1080
    lat_box_side = random.uniform(0.1, 3.0) # degrees

    box, url, image_fn = get_random_venus_image(width, height, lat_box_side)

    twitter = BotTweet(
        "Venus, latitude: %.1f longitude: %.1f, %.1f km wide. %s" % 
        (box.lat, box.lng, box.box_width_km, url))
    twitter.publish_with_image(image_fn)

    os.remove(image_fn)

if __name__ == '__main__':
    main()
