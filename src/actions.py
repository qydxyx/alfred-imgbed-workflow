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


def main(argv):
    url = (argv[1] if len(argv) > 1 else "").strip()
    origin = origin_from_env()
    dash = dashboard_url(url, origin)
    markdown = "![]({})".format(url)
    html = '<img src="{}" alt="">'.format(url)
    items = [
        {
            "uid": "copy",
            "title": "复制图床链接",
            "subtitle": url,
            "arg": url,
            "variables": {"action": "copy"},
        },
        {
            "uid": "markdown",
            "title": "复制 Markdown",
            "subtitle": markdown,
            "arg": markdown,
            "variables": {"action": "copy"},
        },
        {
            "uid": "html",
            "title": "复制 HTML",
            "subtitle": html,
            "arg": html,
            "variables": {"action": "copy"},
        },
        {
            "uid": "open",
            "title": "在浏览器打开图片",
            "subtitle": url,
            "arg": url,
            "variables": {"action": "open"},
        },
        {
            "uid": "dashboard",
            "title": "打开图床后台（编辑 / 管理）",
            "subtitle": dash,
            "arg": dash,
            "variables": {"action": "open"},
        },
    ]
    sys.stdout.write(json.dumps({"items": items}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)
