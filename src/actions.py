#!/usr/bin/env python3
"""Alfred Script Filter items after a successful ImgBed upload."""

from __future__ import print_function

import json
import os
import sys

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


def origin_from_env():
    raw = (os.environ.get("imgbed_url") or "").strip().rstrip("/")
    if raw.lower().endswith("/upload"):
        raw = raw[: -len("/upload")].rstrip("/")
    return raw


def dashboard_url(image_url, origin):
    if origin:
        return origin + "/dashboard"
    parsed = urlparse(image_url)
    if parsed.scheme and parsed.netloc:
        return "{}://{}/dashboard".format(parsed.scheme, parsed.netloc)
    return image_url


def item(uid, title, subtitle, arg, action):
    return {
        "uid": uid,
        "title": title,
        "subtitle": subtitle,
        "arg": arg,
        "valid": True,
        "match": title,
        "variables": {"action": action},
    }


def main(argv):
    url = (argv[1] if len(argv) > 1 else "").strip()
    if not url:
        url = (os.environ.get("image_url") or os.environ.get("query") or "").strip()
    origin = origin_from_env()
    dash = dashboard_url(url, origin)
    markdown = "![]({})".format(url)
    html = '<img src="{}" alt="">'.format(url)
    items = [
        item("copy", "Copy image URL", url, url, "copy"),
        item("markdown", "Copy Markdown", markdown, markdown, "copy"),
        item("html", "Copy HTML", html, html, "copy"),
        item("open", "Open image in browser", url, url, "open"),
        item("dashboard", "Open ImgBed dashboard", dash, dash, "open"),
    ]
    sys.stdout.write(json.dumps({"items": items}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)
