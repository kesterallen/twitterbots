#!/usr/bin/env python3
"""
Bluesky Jetstream reply bot.

Monitors public Bluesky posts for configured phrases and replies with a
random response. Uses the Jetstream/AT Protocol.
"""

import argparse
import datetime
import json
import random
import time
from pathlib import Path
from urllib.parse import urlencode

import websocket
from atproto import Client, models

from blueskybot_lib import BotPost


SLEEP_ERROR = 90
SLEEP_TWEET = 2700
SLEEP_DUPLICATE = 10

JETSTREAM_ENDPOINTS = [
    "wss://jetstream.us-west.bsky.network/xrpc/network.bsky.jetstream.subscribeEvents",
    "wss://jetstream.us-east.bsky.network/xrpc/network.bsky.jetstream.subscribeEvents",
]

DEFAULT_TRACKS = [
    "harpo marx",
    "harpomarx",
    "#harpomarx",
]

DEFAULT_REPLIES = [
    "*hands you a fish*",
    "*hides frog in hat*",
    "Honk honk",
    "Honk honk",
    "Honk honk",
    "Honk honk",
    "Honk honk",
    "Honk honk honk",
    "Honk honk honk",
    "Honk honk honk",
    "Honk honk honk",
    "*offers you a lollipop*",
    "*runs after blonde*",
    "*shows you photograph of a horse*",
    "*whistles*",
    "*whistles*",
    "*whistles*",
    "*whistles*",
]


def now():
    """Return the current time in a readable format."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_bool(value):
    """Parse common true/false command-line values."""
    value = value.lower()
    if value in {"true", "t", "yes", "y", "1"}:
        return True
    if value in {"false", "f", "no", "n", "0"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def post_url(did, rkey):
    """Build the public Bluesky URL for a post."""
    return f"https://bsky.app/profile/{did}/post/{rkey}"


def get_reply_refs(record, post_uri, post_cid):
    """
    Return the root and parent strong references required by Bluesky.

    For a top-level post, it is both the root and parent. For a post that is
    already a reply, retain its original root and use the post itself as the
    parent so the bot replies in the correct place in the thread.
    """
    parent = models.ComAtprotoRepoStrongRef.Main(
        uri=post_uri,
        cid=post_cid,
    )

    reply = record.get("reply") or {}
    root_data = reply.get("root")

    if root_data and root_data.get("uri") and root_data.get("cid"):
        root = models.ComAtprotoRepoStrongRef.Main(
            uri=root_data["uri"],
            cid=root_data["cid"],
        )
    else:
        root = parent

    return models.AppBskyFeedPost.ReplyRef(root=root, parent=parent)


class BlueskyReplyBot:
    """Consume Jetstream posts and reply to matching posts."""

    def __init__(self, args):
        self.args = args
        self.tracks = [phrase.strip().casefold()
                       for phrase in args.track.split(",") if phrase.strip()]
        self.replies = [reply.strip()
                        for reply in args.replies.split(",") if reply.strip()]
        if not self.tracks:
            raise ValueError("At least one --track phrase is required.")
        if not self.replies:
            raise ValueError("At least one --replies response is required.")

        # Use the shared credentials file and the same bot-name convention
        # as the other publishing scripts in blueskybot_lib.
        handle, password = BotPost(botname="replybot").bluesky_credentials

        self.client = Client()
        self.client.login(handle, password)
        self.bot_did = self.client.me.did
        self.cursor_file = Path(args.cursor_file)
        self.cursor = self._load_cursor()

        print(f"{now()} Logged in as {self.client.me.handle}")
        print(f"{now()} Tracking: {', '.join(self.tracks)}")
        print(f"{now()} Replying enabled: {self.args.sendtweet}")

    def _load_cursor(self):
        """Load the last processed Jetstream sequence number, if present."""
        try:
            value = int(self.cursor_file.read_text(encoding="utf-8").strip())
            return value
        except (OSError, ValueError):
            return None

    def _save_cursor(self, seq):
        """
        Save the next sequence to request.

        Jetstream cursors are inclusive, so save seq + 1 to avoid replaying
        the event that was just processed.
        """
        next_cursor = seq + 1
        temp_file = self.cursor_file.with_name(self.cursor_file.name + ".tmp")
        try:
            temp_file.write_text(str(next_cursor), encoding="utf-8")
            temp_file.replace(self.cursor_file)
        finally:
            try:
                temp_file.unlink()
            except FileNotFoundError:
                pass
        self.cursor = next_cursor

    def _matches(self, text):
        text = text.casefold()
        return any(phrase in text for phrase in self.tracks)

    def _send_reply(self, event, record):
        did = event["did"]
        rkey = event["rkey"]
        uri = f"at://{did}/app.bsky.feed.post/{rkey}"
        cid = event.get("cid")
        url = post_url(did, rkey)

        if not cid:
            print(f"{now()} Skipping {url}: Jetstream event has no CID")
            return

        reply = random.choice(self.replies)
        print(f"{now()} {reply} -> {url}")

        if not self.args.sendtweet:
            print(f"Debug: suppressing reply {reply!r}")
            return

        reply_ref = get_reply_refs(record, uri, cid)
        # Do not retry with a different message: if the server accepted the
        # first request but its response was lost, that could create a second
        # reply. Propagate the error so the event can be replayed on reconnect.
        self.client.send_post(text=reply, reply_to=reply_ref)

    def _handle_frame(self, frame):
        """Process one Jetstream JSON frame."""
        message = json.loads(frame)
        event = message.get("payload", message)

        if event.get("$type") != "network.bsky.jetstream.subscribeEvents#commit":
            return

        seq = event.get("seq")
        if (
            event.get("operation") == "create"
            and event.get("collection") == "app.bsky.feed.post"
        ):
            record = event.get("record") or {}
            text = record.get("text", "")
            did = event.get("did")

            # Do not respond to the bot's own posts.
            if text and did != self.bot_did and self._matches(text):
                # If handling fails, leave the cursor unchanged so Jetstream
                # can replay this event after the bot reconnects.
                self._send_reply(event, record)
                time.sleep(self.args.sleep_tweet)

        # Ignored events are safe to skip; matching events reach here only
        # after their reply has completed successfully.
        if seq is not None:
            self._save_cursor(seq)

    def _make_url(self, endpoint):
        params = {
            "collections": "app.bsky.feed.post",
            "kinds": "commit",
        }
        if self.cursor is not None:
            params["cursor"] = str(self.cursor)
        return f"{endpoint}?{urlencode(params)}"

    def run(self):
        """Connect to Jetstream and reconnect after stream/network errors."""
        endpoint_index = 0

        while True:
            endpoint = JETSTREAM_ENDPOINTS[endpoint_index]
            url = self._make_url(endpoint)
            print(f"{now()} Connecting to {endpoint}")

            ws = None
            try:
                ws = websocket.create_connection(
                    url,
                    timeout=60,
                    subprotocols=["xrpc.v1.json"],
                    enable_multithread=True,
                )
                print(f"{now()} Connected to Jetstream")
                print(f"{now()}")

                while True:
                    try:
                        frame = ws.recv()
                        if not frame:
                            raise websocket.WebSocketConnectionClosedException(
                                "Jetstream closed the connection"
                            )
                        self._handle_frame(frame)
                    except websocket.WebSocketTimeoutException:
                        # A quiet stream is normal; keep the connection open.
                        continue

            except KeyboardInterrupt:
                print(f"\\n{now()} Shutting down")
                return
            except Exception as exc:
                print(f"{now()} Stream error: {type(exc).__name__}: {exc}")
                print(f"{now()} Reconnecting in {self.args.sleep_error} seconds")
                print(f"{now()}")
                time.sleep(self.args.sleep_error)
                endpoint_index = (endpoint_index + 1) % len(JETSTREAM_ENDPOINTS)
            finally:
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass


def get_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Bluesky Jetstream reply bot"
    )
    parser.add_argument(
        "--track",
        type=str,
        default=",".join(DEFAULT_TRACKS),
        help="comma-separated tracking phrases (matched case-insensitively)",
    )
    parser.add_argument(
        "--replies",
        type=str,
        default=",".join(DEFAULT_REPLIES),
        help="comma-separated possible replies",
    )
    parser.add_argument(
        "--sendtweet",
        type=parse_bool,
        default=True,
        help="set false for dry-run mode (default: true)",
    )
    parser.add_argument(
        "--sleep_error",
        type=int,
        default=SLEEP_ERROR,
        help="seconds to wait after a stream error",
    )
    parser.add_argument(
        "--sleep_tweet",
        type=int,
        default=SLEEP_TWEET,
        help="seconds to wait after processing a matching post",
    )
    parser.add_argument(
        "--sleep_duplicate",
        type=int,
        default=SLEEP_DUPLICATE,
        help="seconds to wait before retrying a rejected reply",
    )
    parser.add_argument(
        "--cursor-file",
        type=str,
        default="bluesky_replybot.cursor",
        help="file used to persist the Jetstream cursor",
    )
    return parser.parse_args()


def main():
    args = get_args()
    try:
        BlueskyReplyBot(args).run()
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
