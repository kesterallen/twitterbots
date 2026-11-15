"""Module to post to Bluesky for bots (ported from the Twitter/Mastodon version).

Requires:  pip install atproto requests

Credentials file (default ../bluesky_credentials.secret, relative to this file),
one bot per line, whitespace separated:

    <botname> <handle> <app_password>

e.g.

    bluesky_gettysburg.py gettysburg.bsky.social xxxx-xxxx-xxxx-xxxx

Use an *app password* (Settings -> Privacy and Security -> App Passwords),
never your main account password.
"""

import datetime
import inspect
import io
import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests
from atproto import Client, models
from atproto.exceptions import AtProtocolError
from PIL import Image

# Bluesky's limit is 300 graphemes. len() counts code points, which is always
# >= the grapheme count, so this errs on the safe side.
MAX_POST_LEN = 300

# Bluesky rejects image blobs larger than 1,000,000 bytes
MAX_IMAGE_BYTES = 950_000

MONITOR_DIR = Path.home()


def shrink_image(data: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    """
    Return image bytes under max_bytes, as JPEG. Images already small enough
    are returned untouched. Otherwise, downscale and lower JPEG quality until
    the image fits.
    """
    if len(data) <= max_bytes:
        return data

    img = Image.open(io.BytesIO(data))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    quality = 90
    while True:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= max_bytes:
            return buf.getvalue()
        if quality > 60:
            quality -= 10
        else:
            img = img.resize((int(img.width * 0.85), int(img.height * 0.85)))


def download_image(image_url: str, timeout: int = 60) -> bytes:
    """Download an image and return its (Bluesky-size-compliant) bytes"""
    resp = requests.get(image_url, timeout=timeout)
    resp.raise_for_status()
    return shrink_image(resp.content)


class _OpenGraphParser(HTMLParser):
    """Collect <meta property|name="og:*|twitter:*" content="..."> tags and <title>"""

    def __init__(self):
        super().__init__()
        self.meta = {}
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            if key and attrs.get("content") is not None:
                self.meta.setdefault(key.strip().lower(), attrs["content"].strip())
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def fetch_open_graph(page_url: str, timeout: int = 60) -> dict:
    """
    Fetch a page and return {'url', 'title', 'description', 'image'} from its
    OpenGraph (falling back to Twitter-card / <title>) metadata. A relative
    image URL is resolved against the page URL.
    """
    resp = requests.get(
        page_url,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; tweetbot_lib link-card fetcher)"},
    )
    resp.raise_for_status()
    parser = _OpenGraphParser()
    parser.feed(resp.text)
    meta = parser.meta

    image = meta.get("og:image") or meta.get("twitter:image")
    return {
        "url": meta.get("og:url") or page_url,
        "title": meta.get("og:title") or meta.get("twitter:title") or parser.title.strip(),
        "description": meta.get("og:description") or meta.get("twitter:description") or "",
        "image": urljoin(page_url, image) if image else None,
    }


class BotPost:
    """Bot post module"""

    @classmethod
    def _get_botname(cls) -> str:
        frameinfo = inspect.stack()[-1]
        return os.path.basename(frameinfo.filename)

    @classmethod
    def run_recently(cls, seconds: int = 86400, botname: str = None) -> bool:
        """
        True if this bot ran within the last 'seconds' seconds. Otherwise,
        touch the monitor file and return False.
        """
        if botname is None:
            botname = cls._get_botname()

        monitor_file = MONITOR_DIR / f".monitor_{botname}.txt"

        if monitor_file.is_file():
            last_modified = datetime.datetime.fromtimestamp(monitor_file.stat().st_mtime)
            age = datetime.datetime.now() - last_modified
            if age.total_seconds() <= seconds:
                return True

        monitor_file.write_text(str(datetime.datetime.now()), encoding="utf-8")
        return False

    def __init__(self, word: str = None, botname: str = None) -> None:
        """Truncate word to MAX_POST_LEN if necessary"""
        self.botname = BotPost._get_botname() if botname is None else botname
        self.words = [] if word is None else [word[:MAX_POST_LEN]]

    def pop(self) -> str:
        """Pop a word off of self.words"""
        return self.words.pop()

    def append(self, word: str) -> None:
        """Append 'word' to the self.words list, truncating if necessary"""
        self.words.append(word[:MAX_POST_LEN])

    def can_take_new_word(self, word: str) -> bool:
        """Will post be under the length limit after adding a new word"""
        return not self.will_be_too_long(word)

    def will_be_too_long(self, word: str) -> bool:
        """Will post be too long after adding a new word"""
        assert isinstance(word, str)
        # +1 for the joining space (zero words -> no space)
        sep = 1 if self.words else 0
        return self.len + sep + len(word) > MAX_POST_LEN

    def set_text(self, text: str) -> None:
        """Set the words array to input text"""
        self.words = [text]

    @property
    def len(self) -> int:
        """Length of post text"""
        return len(self.str)

    @property
    def is_too_long(self) -> bool:
        """Does post length exceed MAX_POST_LEN"""
        return self.len > MAX_POST_LEN

    @property
    def str(self) -> str:
        """String representation of text"""
        return " ".join(self.words)

    # ---- Bluesky auth ----------------------------------------------------

    @property
    def bluesky_credentials(self) -> tuple:
        """(handle, app_password) from the default credentials file"""
        return self.bluesky_credentials_from_file()

    def bluesky_credentials_from_file(
        self, file: str = "../bluesky_credentials.secret"
    ) -> tuple:
        """
        Handle and app password for this bot. Assumes the file is at
        ../bluesky_credentials.secret unless specified otherwise. Each line is:

            <botname> <handle> <app_password>
        """
        path = os.path.join(os.path.dirname(__file__), file)
        with open(path, encoding="utf-8") as fh:
            for row in fh:
                parts = row.split()
                if len(parts) == 3 and parts[0] == self.botname:
                    return parts[1], parts[2]
        raise KeyError(f"No Bluesky credentials for bot '{self.botname}' in {path}")

    def _get_bluesky(self) -> Client:
        handle, app_password = self.bluesky_credentials
        client = Client()
        client.login(handle, app_password)
        return client

    # ---- Publishing ------------------------------------------------------

    def publish(self) -> None:
        """Publish to Bluesky"""
        if self.is_too_long:
            raise ValueError(f"Post is {self.len} chars; limit is {MAX_POST_LEN}")
        try:
            client = self._get_bluesky()
            client.send_post(self.str)
        except FileNotFoundError as err:
            print(f"Can't find file: {err}")
        except KeyError as err:
            print(f"Credentials error: {err}")
        except AtProtocolError as err:
            print(f"Bluesky error: {err}")

    def _send_image_bytes(self, image_data: bytes, alt_text: str = "") -> None:
        if self.is_too_long:
            raise ValueError(f"Post is {self.len} chars; limit is {MAX_POST_LEN}")
        try:
            client = self._get_bluesky()
            client.send_image(text=self.str, image=image_data, image_alt=alt_text)
        except KeyError as err:
            print(f"Credentials error: {err}")
        except FileNotFoundError as err:
            print(f"Can't find file: {err}")
        except AtProtocolError as err:
            print(f"Bluesky error: {err}")

    def publish_with_image(self, image_fn: str, alt_text: str = "") -> None:
        """Publish to Bluesky with an image from a local file"""
        with open(image_fn, "rb") as image:
            data = shrink_image(image.read())
        self._send_image_bytes(data, alt_text)

    def publish_with_image_url(self, image_url: str, alt_text: str = "") -> None:
        """
        Download the image at image_url and publish it to Bluesky as an
        embedded image (not just a link to it).
        """
        try:
            data = download_image(image_url)
        except requests.RequestException as err:
            print(f"Can't download image {image_url}: {err}")
            return
        self._send_image_bytes(data, alt_text)

    def publish_with_link_card(self, page_url: str, include_link: bool = False) -> None:
        """
        Publish to Bluesky with a link-preview card built from page_url's
        OpenGraph tags.

        Bluesky does NOT scrape OpenGraph tags when a post is created through
        the API -- the official app builds the card client-side while you
        type, and attaches it to the post. A bot has to do the same: fetch the
        tags, upload the image as a blob, and attach an external embed.
        """
        if self.is_too_long:
            raise ValueError(f"Post is {self.len} chars; limit is {MAX_POST_LEN}")
        try:
            og = fetch_open_graph(page_url)
            client = self._get_bluesky()

            thumb = None
            if og["image"]:
                try:
                    thumb = client.upload_blob(download_image(og["image"])).blob
                except (requests.RequestException, AtProtocolError) as err:
                    print(f"Can't attach card image {og['image']}: {err}")

            embed = models.AppBskyEmbedExternal.Main(
                external=models.AppBskyEmbedExternal.External(
                    uri=page_url,
                    title=og["title"],
                    description=og["description"],
                    thumb=thumb,
                )
            )
            text = f"{self.str} {page_url}" if include_link else self.str
            client.send_post(text, embed=embed)
        except requests.RequestException as err:
            print(f"Can't fetch {page_url}: {err}")
        except KeyError as err:
            print(f"Credentials error: {err}")
        except AtProtocolError as err:
            print(f"Bluesky error: {err}")

    def download_post_text(self, post_api_url: str) -> None:
        """
        Get a post's text from an API, which should return a JSON object
        with a 'tweet' key
        """
        resp = requests.get(post_api_url, timeout=60)
        resp.raise_for_status()
        self.words = [resp.json()["tweet"][:MAX_POST_LEN]]

    def __repr__(self) -> str:
        return self.str


# Backwards-compatible aliases so existing bot scripts keep working
BotTweet = BotPost
MAX_TWEET_LEN = MAX_POST_LEN


def get_post_filename(filename: str) -> str:
    """Assume the text file is in ../txt/"""
    return os.path.join(os.path.dirname(__file__), f"../txt/{filename}")


get_tweet_filename = get_post_filename


def postify_text(textfile, use_lines: bool = False) -> list:
    """
    Break the text file into MAX_POST_LEN-char-or-less BotPost objects.

    If use_lines is True, make one post per line in the file.
    """

    def _posts_by_line(file_) -> list:
        """One file line per post, truncated to MAX_POST_LEN if necessary."""
        return [BotPost(line.strip()) for line in file_ if line.strip()]

    def _posts_by_word(file_) -> list:
        """
        Fill each post until it can't take another word without getting too
        long, then start a new post with the current word.
        """
        posts = []
        post = BotPost()
        for word in file_.read().split():
            if post.can_take_new_word(word):
                post.append(word)
            else:
                posts.append(post)
                post = BotPost(word)
        posts.append(post)  # the file's final post
        return posts

    with open(textfile, encoding="utf-8") as file_:
        return _posts_by_line(file_) if use_lines else _posts_by_word(file_)


tweetify_text = postify_text


def get_today_index(num_posts: int, start_date: datetime.datetime) -> int:
    """Today's index into a list that is num_posts long, starting at start_date"""
    td_since_start = datetime.datetime.now() - start_date
    return td_since_start.days % num_posts


def get_today_post(posts: list, start_date: datetime.datetime) -> BotPost:
    """Get today's post from the list 'posts' starting at 'start_date'"""
    return posts[get_today_index(len(posts), start_date)]


get_today_tweet = get_today_post


def parse_text_and_get_today_post(
    textfile: str, start_date: datetime.datetime, use_lines: bool = False
) -> BotPost:
    """Get today's post from a text file, starting at 'start_date'"""
    posts = postify_text(get_post_filename(textfile), use_lines)
    return get_today_post(posts, start_date)


parse_text_and_get_today_tweet = parse_text_and_get_today_post
