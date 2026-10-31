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
        raise ValueError("请在 Workflow 配置里填写 imgbed_url")
    url = url.rstrip("/")
    if url.lower().endswith("/upload"):
        url = url[: -len("/upload")].rstrip("/")
    if not url.lower().startswith("https://"):
        raise ValueError("imgbed_url 必须是 https:// 开头")
    return url


def pick_url(payload):
    if isinstance(payload, list):
        if not payload:
            raise ValueError("上传成功但响应是空数组")
        item = payload[0]
    elif isinstance(payload, dict):
        item = payload
    else:
        raise ValueError("响应不是 JSON 数组或对象")
    if not isinstance(item, dict):
        raise ValueError("响应缺少 src")
    url = (item.get("publicUrl") or item.get("src") or "").strip()
    if not url:
        raise ValueError("响应缺少 src")
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
        raise RuntimeError(detail or "sips 转换失败")
    return dst


def prepare_file(path, tmp_dir):
    if not path or not os.path.isfile(path):
        fail("找不到图片文件")
    ext = extension(path)
    if ext in CONVERT_EXT:
        try:
            return convert_to_png(path, tmp_dir)
        except Exception as exc:
            fail("无法将 TIFF 转为 PNG：{}".format(exc))
    if ext not in ALLOWED_EXT:
        fail("不支持的图片格式（{}）。请用 PNG / JPEG / GIF / WebP".format(ext or "无扩展名"))
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
        fail("读取剪贴板失败")
    text = result.stdout.decode("utf-8", "replace").strip()
    if not text or text == "none":
        fail("剪贴板里没有图片")
    kind, _, value = text.partition("\t")
    path = value.strip()
    if kind == "file":
        return prepare_file(path, tmp_dir)
    if kind in ("png", "tiff"):
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            fail("剪贴板里没有图片")
        return prepare_file(path, tmp_dir)
    fail("剪贴板里没有图片")


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
        raise RuntimeError(stderr or "网络错误")
    if "\n" not in stdout:
        raise RuntimeError(stdout.strip() or "空响应")
    body, _, status = stdout.rpartition("\n")
    return status.strip(), body.strip(), stderr


def explain_http(status, body):
    if status == "401":
        return "401 Unauthorized：认证码错误或未填写，请在 Workflow 配置里填写用户认证码"
    if status == "403":
        return "403：当前 IP 被封禁"
    if status == "400":
        return "400：文件类型或内容不被接受" + ("（{}）".format(body) if body else "")
    if status == "500":
        return "500：服务器错误" + ("（{}）".format(body[:200]) if body else "")
    if status == "000":
        return "网络错误或超时"
    return "上传失败 HTTP {} {}".format(status, body[:200]).strip()


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
                log("已忽略其余 {} 张，只上传第一张".format(extra - 1))
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
            fail("无法解析上传响应")

        if url.startswith("/"):
            url = origin + url

        filename = os.path.basename(path)
        if extra > 1:
            filename = "{}（及忽略 {} 张）".format(filename, extra - 1)
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
        fail("内部错误，请看 Alfred Debugger")
