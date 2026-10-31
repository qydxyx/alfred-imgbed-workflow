# CloudFlare ImgBed for Alfred

把 Finder 选中的图片，或剪贴板里的截图，上传到自建 [CloudFlare ImgBed](https://github.com/MarSeventh/CloudFlare-ImgBed)。成功后弹出通知、把链接写入剪贴板，并在 Alfred 里给出后续操作。失败不改剪贴板。

需要 Alfred 5 Powerpack。

## 安装

1. 从 [Releases](https://github.com/qydxyx/alfred-imgbed-workflow/releases) 下载 `CloudFlare-ImgBed.alfredworkflow` 并双击
2. 开发可把本仓库链到 Alfred 的 workflows 目录
2. 打开 Alfred → Workflows → **CloudFlare ImgBed** → 右上角 `[x]`
3. 填写：
   - **ImgBed URL**：例如 `https://cloudflare-imgbed.qydxyx.workers.dev`（不要尾斜杠）
   - **Auth Code**：ImgBed 后台的「用户认证码」，不是管理员密码
   - **Upload Channel**：已绑 R2 就用 `cfr2`
4. 双击画布上的 Hotkey，设一个快捷键

`/usr/bin/python3` 需要 [Xcode Command Line Tools](https://developer.apple.com/xcode/resources/)。没装时第一次运行会弹安装框。

## 用法

| 场景 | 怎么做 |
| --- | --- |
| Finder 里的图片文件 | 选中文件 → Universal Action（默认 `⌘/`）→ **Upload to ImgBed**（匹配全部 `public.image`，含 PNG / JPEG / GIF / WebP / TIFF） |
| 剪贴板截图 | `⌘⌃⇧4` 复制到剪贴板 → 按 Hotkey，或 Alfred 里输入 `imgbed` |
| 桌面截图文件 | `⌘⇧4` 存到桌面 → 选中该文件 → Universal Action |
| 测试连接 | Alfred 里输入 `imgbed-test`（会上传一张 1×1 PNG） |

`⌘⇧4` 默认把文件存到桌面，不会进剪贴板。剪贴板截图用 `⌘⌃⇧4`。

## 行为

- 成功：系统通知显示 URL；链接写入剪贴板（无尾换行）；Alfred 列出可选项
  - 复制图床链接 / Markdown / HTML
  - 在浏览器打开图片
  - 打开图床后台 `/dashboard`（登录后可编辑、删除）
- 失败：系统通知显示原因（无图、401、网络错误等），**不改**剪贴板
- TIFF 截图会先转成 PNG
- 多选文件只传第一张
- 认证码走 `authCode` 请求头，不放在 URL 上
- `returnFormat=full`、`autoRetry=false` 写死，失败不会静默换渠道

## 命令行

配置通过环境变量传入，和 Workflow Configuration 同名：

```bash
export imgbed_url="https://cloudflare-imgbed.qydxyx.workers.dev"
export auth_code="YOUR_CODE"
export upload_channel="cfr2"

/usr/bin/python3 src/upload.py /path/to/image.png
/usr/bin/python3 src/upload.py            # 读剪贴板
/usr/bin/python3 src/upload.py --test
```

## 发版

每个 `v*` tag 会打一个 GitHub Release，附件是 `CloudFlare-ImgBed.alfredworkflow`（不含认证码）。

```bash
# 1. 改 info.plist 里的 version，例如 1.1.0
# 2. 提交后打 tag
git tag v1.1.0
git push origin v1.1.0
```

本地预览包：

```bash
bash scripts/package.sh
```

## 常见错误

| 提示 | 处理 |
| --- | --- |
| 剪贴板里没有图片 | 确认复制的是图，不是文字；截图请用 `⌘⌃⇧4` |
| 401 Unauthorized | 在 `[x]` 里填写用户认证码 |
| 不支持的图片格式 | 用 PNG / JPEG / GIF / WebP。HEIC 首版不支持 |
| `/usr/bin/python3` 弹安装框 | 安装 Xcode Command Line Tools |
