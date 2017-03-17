
import datetime
import math
import os
from PIL import Image, ImageOps
import random
from tweetbot_lib import BotTweet, get_keys
import urllib

KEY_FILE = 'keys.txt'

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

def get_bounding_box():
    # Math from http://mathworld.wolfram.com/SpherePointPicking.html
    rand_u = random.random()
    rand_v = random.random()
    lng = 360.0 * rand_u # Range: [0.0, 360.0]
    lat = math.acos(2.0 * rand_v - 1) * 180.0 / math.pi - 90.0 # Range: [-90.0, 90.0]

    # Convert latitude to radans for the cos operation
    lat_rad = lat * math.pi / 180.0

    d_lng = 1.5 # for example
    d_lat = d_lng / math.cos(abs(lat_rad))

    return lng, lat, lng + d_lng, lat + d_lat

def get_image(width, height, image_fn):
    # Get a subimage without too many blank pixels:
    #
    image_too_dark = True
    while image_too_dark:
        lng, lat, lng_end, lat_end = get_bounding_box()
        str_box = "%s,%s,%s,%s" % (lng, lat, lng_end, lat_end)
        url = IMG_TMPL % (str_box, width, height)
        urllib.urlretrieve(url, image_fn)
        image = Image.open(image_fn)
        image_too_dark = image.histogram()[0] > sum(image.histogram()[1:])

    image = ImageOps.autocontrast(image)
    image.save(image_fn)

    return lng, lat, image_fn

def main():
    width = 1920
    height = 1080
    image_fn = "venus.jpg"
    lng, lat, image_fn = get_image(width, height, image_fn)

    keys = get_keys(KEY_FILE, __file__)
    twitter = BotTweet()
    twitter.words = ["Venus, latitude: %.5f longitude: %.5f" % (lat, lng)]
    twitter.publish_with_image(image_fn, *keys)

    os.remove(image_fn)

if __name__ == '__main__':
    main()
