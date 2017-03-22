
import attrdict
import math
import os
from PIL import Image, ImageOps
import random
from tweetbot_lib import BotTweet
import urllib

# Thanks to Trent Hare of the USGS for pointing this service out:
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
        image = Image.open(image_fn)
        pct_black = float(image.histogram()[0]) / float(sum(image.histogram()))
        image_too_dark = pct_black > max_pct_black

    image = ImageOps.autocontrast(image)
    image.save(image_fn)

    return box, url, image_fn

def main():
    width = 1920
    height = 1080
    lat_box_side = random.uniform(0.5, 5.0) # degrees

    box, url, image_fn = get_random_venus_image(width, height, lat_box_side)

    twitter = BotTweet()
    twitter.words = [
        "Venus, latitude: %.1f " % box.lat,
        "longitude: %.1f, " % box.lng,
        "%.1f km wide. %s" % (box.box_width_km, url)
    ]
    twitter.publish_with_image(image_fn)

    os.remove(image_fn)

if __name__ == '__main__':
    main()
