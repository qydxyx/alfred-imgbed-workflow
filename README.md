# CloudFlare ImgBed for Alfred

Upload a Finder image or a clipboard screenshot to a self-hosted [CloudFlare ImgBed](https://github.com/MarSeventh/CloudFlare-ImgBed). On success, Alfred shows a notification, copies the URL, and offers follow-up actions. On failure the clipboard is left unchanged.

Requires Alfred 5 Powerpack.

## Install

1. Download `CloudFlare-ImgBed.alfredworkflow` from [Releases](https://github.com/qydxyx/alfred-imgbed-workflow/releases) and double-click it
2. For development, symlink this repo into Alfred’s workflows folder
3. Open Alfred → Workflows → **CloudFlare ImgBed** → `[x]`
4. Fill in:
   - **ImgBed URL**: for example `https://cloudflare-imgbed.qydxyx.workers.dev` (no trailing slash)
   - **Auth Code**: the user auth code from the ImgBed admin, not the admin password
   - **Upload Channel**: `cfr2` if R2 is bound
5. Double-click the Hotkey object and assign a shortcut

`/usr/bin/python3` needs [Xcode Command Line Tools](https://developer.apple.com/xcode/resources/). macOS prompts to install them on first run if they are missing.

## Usage

| Situation | How |
| --- | --- |
| Image file in Finder | Select the file → Universal Action (default `⌘/`) → **Upload to ImgBed** (matches `public.image`: PNG / JPEG / GIF / WebP / TIFF) |
| Clipboard screenshot | `⌘⌃⇧4` to copy → Hotkey, or type `imgbed` in Alfred |
| Screenshot saved to Desktop | `⌘⇧4` → select the file → Universal Action |
| Connection test | Type `imgbed-test` in Alfred (uploads a 1×1 PNG) |

`⌘⇧4` saves a file to the Desktop by default. Use `⌘⌃⇧4` for a clipboard screenshot.

## Behavior

- Success: system notification with the URL; URL copied to the clipboard (no trailing newline); Alfred lists actions
  - Copy image URL / Markdown / HTML
  - Open the image in a browser
  - Open the ImgBed `/dashboard` (sign in to edit or delete)
- Failure: notification with the reason (no image, 401, network error, …); clipboard unchanged
- TIFF screenshots are converted to PNG first
- Multiple selected files: only the first is uploaded
- Auth code is sent in the `authCode` header, not in the URL
- `returnFormat=full` and `autoRetry=false` are fixed; a failed channel is not retried silently

## Command line

Configuration is passed as environment variables with the same names as Workflow Configuration:

```bash
export imgbed_url="https://cloudflare-imgbed.qydxyx.workers.dev"
export auth_code="YOUR_CODE"
export upload_channel="cfr2"

/usr/bin/python3 src/upload.py /path/to/image.png
/usr/bin/python3 src/upload.py            # clipboard
/usr/bin/python3 src/upload.py --test
```

## Releases

Each `v*` tag creates a GitHub Release with `CloudFlare-ImgBed.alfredworkflow` (auth code excluded).

```bash
# 1. Bump version in info.plist, e.g. 1.1.5
# 2. Commit, then tag
git tag v1.1.5
git push origin v1.1.5
```

Package locally:

```bash
bash scripts/package.sh
```

## Common errors

| Message | What to do |
| --- | --- |
| No image on the clipboard | Confirm the clipboard holds an image, not text; use `⌘⌃⇧4` for screenshots |
| 401 Unauthorized | Set the user auth code in `[x]` |
| Unsupported image format | Use PNG / JPEG / GIF / WebP. HEIC is not supported |
| `/usr/bin/python3` install prompt | Install Xcode Command Line Tools |
