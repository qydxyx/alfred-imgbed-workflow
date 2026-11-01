#!/usr/bin/env python3
"""Upload an image to CloudFlare ImgBed. Copy the URL only on success."""

from __future__ import print_function

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
CONVERT_EXT = {".tif", ".tiff"}
MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

CLIPBOARD_SCRIPT = r"""
on run argv
    set pngPath to item 1 of argv
    set tiffPath to item 2 of argv

    -- Coercing text to «class furl» succeeds with a fake path. Only use
    -- file URLs when the pasteboard actually contains that flavor.
    if (clipboard info for «class furl») is not {} then
        try
            set theFile to POSIX path of (the clipboard as «class furl»)
            return "file" & tab & theFile
        end try
    end if

    if (clipboard info for «class PNGf») is not {} then
        try
            set pngData to the clipboard as «class PNGf»
            do shell script "/usr/bin/touch " & quoted form of pngPath
            set fRef to open for access (POSIX file pngPath) with write permission
            set eof fRef to 0
            write pngData to fRef
            close access fRef
            return "png" & tab & pngPath
        on error
            try
                close access (POSIX file pngPath)
            end try
        end try
    end if

    if (clipboard info for TIFF picture) is not {} then
        try
            set tiffData to the clipboard as TIFF picture
            do shell script "/usr/bin/touch " & quoted form of tiffPath
            set fRef to open for access (POSIX file tiffPath) with write permission
            set eof fRef to 0
            write tiffData to fRef
            close access fRef
            return "tiff" & tab & tiffPath
        on error
            try
                close access (POSIX file tiffPath)
            end try
        end try
    end if

    return "none"
end run
"""


def log(msg):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.stderr.flush()


def copy_url(url):
    subprocess.run(["/usr/bin/pbcopy"], input=url.encode("utf-8"), check=True)


def fail(message):
    log(message)
    sys.stdout.write(message)
    sys.exit(1)


def succeed(url, filename):
    copy_url(url)
    log("uploaded {} -> {}".format(filename, url))
    sys.stdout.write(url)
    sys.exit(0)


def normalize_origin(raw):
    url = (raw or "").strip()
    if not url:
        raise ValueError("Set imgbed_url in Workflow Configuration")
    url = url.rstrip("/")
    if url.lower().endswith("/upload"):
        url = url[: -len("/upload")].rstrip("/")
    if not url.lower().startswith("https://"):
        raise ValueError("imgbed_url must start with https://")
    return url


def pick_url(payload):
    if isinstance(payload, list):
        if not payload:
            raise ValueError("Upload succeeded but the response array is empty")
        item = payload[0]
    elif isinstance(payload, dict):
        item = payload
    else:
        raise ValueError("Response is not a JSON array or object")
    if not isinstance(item, dict):
        raise ValueError("Response is missing src")
    url = (item.get("publicUrl") or item.get("src") or "").strip()
    if not url:
        raise ValueError("Response is missing src")
    return url


def extension(path):
    return os.path.splitext(path)[1].lower()


def first_path(args):
    if not args:
        return None, 0
    parts = []
    for arg in args:
        parts.extend([p for p in arg.split("\t") if p])
    return (parts[0] if parts else None), len(parts)


def convert_to_png(src, tmp_dir):
    dst = os.path.join(tmp_dir, "converted-{}.png".format(os.getpid()))
    result = subprocess.run(
        ["/usr/bin/sips", "-s", "format", "png", src, "--out", dst],
        capture_output=True,
    )
    if result.returncode != 0 or not os.path.isfile(dst) or os.path.getsize(dst) == 0:
        detail = (result.stderr or result.stdout).decode("utf-8", "replace").strip()
        raise RuntimeError(detail or "sips conversion failed")
    return dst


def prepare_file(path, tmp_dir):
    if not path or not os.path.isfile(path):
        fail("Image file not found")
    ext = extension(path)
    if ext in CONVERT_EXT:
        try:
            return convert_to_png(path, tmp_dir)
        except Exception as exc:
            fail("Could not convert TIFF to PNG: {}".format(exc))
    if ext not in ALLOWED_EXT:
        fail("Unsupported image format ({}). Use PNG / JPEG / GIF / WebP".format(ext or "no extension"))
    return path


def clipboard_image(tmp_dir):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    png_path = os.path.join(tmp_dir, "imgbed-{}-{}.png".format(stamp, os.getpid()))
    tiff_path = os.path.join(tmp_dir, "imgbed-{}-{}.tiff".format(stamp, os.getpid()))
    result = subprocess.run(
        ["/usr/bin/osascript", "-", png_path, tiff_path],
        input=CLIPBOARD_SCRIPT.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        fail("Could not read the clipboard")
    text = result.stdout.decode("utf-8", "replace").strip()
    if not text or text == "none":
        fail("No image on the clipboard")
    kind, _, value = text.partition("\t")
    path = value.strip()
    if kind == "file":
        return prepare_file(path, tmp_dir)
    if kind in ("png", "tiff"):
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            fail("No image on the clipboard")
        return prepare_file(path, tmp_dir)
    fail("No image on the clipboard")


def write_test_png(tmp_dir):
    path = os.path.join(tmp_dir, "imgbed-test-{}.png".format(os.getpid()))
    with open(path, "wb") as handle:
        handle.write(PNG_1X1)
    return path


def upload(path, origin, auth_code, channel):
    query = ["returnFormat=full", "autoRetry=false"]
    if channel:
        query.append("uploadChannel=" + channel)
    url = origin + "/upload?" + "&".join(query)
    ext = extension(path) or ".png"
    mime = MIME.get(ext, "application/octet-stream")
    filename = os.path.basename(path) or ("image" + ext)
    safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename) or ("image" + ext)
    cmd = [
        "/usr/bin/curl",
        "-sS",
        "--max-time",
        "30",
        "-w",
        "\n%{http_code}",
    ]
    if auth_code:
        cmd.extend(["-H", "authCode: " + auth_code])
    cmd.extend([
        "-F",
        "file=@-;filename={};type={}".format(safe_name, mime),
        url,
    ])
    with open(path, "rb") as handle:
        data = handle.read()
    result = subprocess.run(cmd, input=data, capture_output=True)
    stdout = result.stdout.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8", "replace").strip()
    if result.returncode != 0:
        raise RuntimeError(stderr or "Network error")
    if "\n" not in stdout:
        raise RuntimeError(stdout.strip() or "Empty response")
    body, _, status = stdout.rpartition("\n")
    return status.strip(), body.strip(), stderr


def explain_http(status, body):
    if status == "401":
        return "401 Unauthorized: auth code is wrong or missing. Set it in Workflow Configuration"
    if status == "403":
        return "403: this IP is blocked"
    if status == "400":
        return "400: file type or contents rejected" + (" ({})".format(body) if body else "")
    if status == "500":
        return "500: server error" + (" ({})".format(body[:200]) if body else "")
    if status == "000":
        return "Network error or timeout"
    return "Upload failed HTTP {} {}".format(status, body[:200]).strip()


def main(argv):
    test_mode = False
    args = []
    for arg in argv[1:]:
        if arg == "--test":
            test_mode = True
        elif arg:
            args.append(arg)

    try:
        origin = normalize_origin(os.environ.get("imgbed_url", ""))
    except ValueError as exc:
        fail(str(exc))

    auth_code = (os.environ.get("auth_code") or "").strip()
    channel = (os.environ.get("upload_channel") or "").strip()

    tmp_dir = tempfile.mkdtemp(prefix="imgbed-")
    extra = 0
    try:
        if test_mode:
            path = write_test_png(tmp_dir)
        else:
            given, extra = first_path(args)
            if extra > 1:
                log("Ignored {} extra file(s); uploading the first only".format(extra - 1))
            if given:
                path = prepare_file(given, tmp_dir)
            else:
                path = clipboard_image(tmp_dir)

        try:
            status, body, curl_err = upload(path, origin, auth_code, channel)
        except RuntimeError as exc:
            fail(str(exc))

        if status != "200":
            fail(explain_http(status, body or curl_err))

        try:
            payload = json.loads(body)
            url = pick_url(payload)
        except (ValueError, json.JSONDecodeError):
            fail("Could not parse the upload response")

        if url.startswith("/"):
            url = origin + url

        filename = os.path.basename(path)
        if extra > 1:
            filename = "{} (ignored {} extra)".format(filename, extra - 1)
        succeed(url, filename)
    finally:
        try:
            for name in os.listdir(tmp_dir):
                try:
                    os.remove(os.path.join(tmp_dir, name))
                except OSError:
                    pass
            os.rmdir(tmp_dir)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main(sys.argv)
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        fail("Internal error; see Alfred Debugger")
