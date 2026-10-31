# Alfred Workflow：CloudFlare ImgBed 剪贴板上传

面向实例 `https://cloudflare-imgbed.qydxyx.workers.dev/`。目标：剪贴板或 Finder 里有图时，一键上传到 ImgBed，成功后把链接写回剪贴板。失败不改剪贴板。

现网已验证：站点需要用户认证码（无 `authCode` 时 `/upload` 返回 `401 Unauthorized`）。

需要 Alfred 5 Powerpack。

## 1. 目标与边界

**要做**

- Finder 选中图片文件，用 File Action 上传
- 剪贴板里的截图 / 复制的图片，用 Hotkey 或 Keyword 上传（脚本自己读剪贴板）
- Workflow 配置里改图床 URL、上传认证码、渠道
- 成功：通知「已上传」，链接写入剪贴板
- 失败：通知可读原因，不改剪贴板

**首版不做**

- 管理端登录、删图、列目录
- 分块上传 / 超大文件
- 多图床账号切换
- GUI 设置面板（用 Alfred Workflow Configuration）
- HEIC / HEIF（从照片 app 复制时提示不支持）
- Markdown / HTML 输出格式
- Universal Action 处理剪贴板像素（Alfred 做不到，见第 4 节）

## 2. 对接 ImgBed 的接口

上传走现成接口，不要自己拼存储渠道。

| 项 | 约定 |
| --- | --- |
| 方法 / 路径 | `POST {origin}/upload` |
| Body | `multipart/form-data`，字段名必须是 `file` |
| 认证 | Header `authCode`（后台「用户认证码」）。此实例必填 |
| 查询参数 | `returnFormat=full`（写死，不做配置项） |
| 渠道 | 默认 `uploadChannel=cfr2` |
| 重试 | `autoRetry=false`（写死）。cfr2 失败就失败，不要静默改走 Telegram |
| 成功响应 | JSON 数组：`[{"src":"https://host/file/<id>","publicUrl":"...可选"}]` |
| 失败 | `401` 认证码错或未填、`403` IP 封禁、`400` 文件损坏/类型不对、`500` 渠道未配置 |

认证提取优先级（服务端）：URL `?authCode=` → Referer → Header `authCode` → Cookie。Workflow 只用 Header，避免密码进访问日志。

链接取值：优先 `publicUrl`（后台配了 urlPrefix 时才有），否则用 `src`。`returnFormat=full` 时 `src` 已是完整 URL。

缺省 `uploadChannel` 时服务端**永远**落到 Telegram，不是后台默认渠道。所以配置里默认填 `cfr2`。

## 3. 使用流程

**文件**

1. Finder 选中一张图
2. Universal Action 热键（Alfred 默认 `⌘/`，以本机为准）
3. 选 **Upload to ImgBed**

**剪贴板图（截图、网页复制）**

1. `⌘⌃⇧4` 复制截图到剪贴板，或在别的 app 里复制图片
2. 按本 workflow 的 Hotkey（安装后自己设），或 Alfred 里输入 `imgbed`
3. 脚本读剪贴板 → 必要时 TIFF 转 PNG → 上传

`⌘⇧4` 默认把 PNG **存到桌面**，不是进剪贴板。对桌面文件用 File Action。

## 4. 工作流结构

独立仓库 `alfred-imgbed-workflow`，不要塞进 CloudFlare-ImgBed。

```text
alfred-imgbed-workflow/
  info.plist
  README.md
  icon.png                 # Alfred 认根目录 icon.png
  src/
    upload.py              # 读文件或剪贴板、上传、成功才 pbcopy、自己弹通知
```

对象图（下游不再接 Copy to Clipboard / Post Notification）：

```text
[File Action: public.image, 单文件]
        \
[Hotkey: 无参数]  →  Run Script: /usr/bin/python3 src/upload.py "$@"
        /
[Keyword: imgbed, 无参数]

[Keyword: imgbed-test, 无参数] → Run Script: /usr/bin/python3 src/upload.py --test
```

原因：Alfred 的 Run Script **不管 exit code 都会把 stdout 交给下一个对象**；stderr 只进 Debugger。若把 Copy to Clipboard 接在后面，失败时空 stdout 会把剪贴板写成空。所以复制和通知都在 Python 里做。

**不要用的接法**

- Hotkey Argument「Clipboard / Image File」：官方 Hotkey 的 Clipboard 只提供文本
- Universal Action 对剪贴板像素：只能作用于选中的文件/文本，不能把剪贴板 TIFF/PNG 数据当成文件

**Workflow Configuration**

- `imgbed_url`：默认 `https://cloudflare-imgbed.qydxyx.workers.dev`，不要尾斜杠。脚本按这个名字读环境变量
- `auth_code`：用户认证码，Password 字段，不进 git，加入 `variablesdontexport`
- `upload_channel`：默认 `cfr2`。可改成 `telegram` / `s3` 等。留空则不传该参数（服务端走 Telegram）

`returnFormat` 不做成配置项。

## 5. 剪贴板图片

macOS 剪贴板经常是 TIFF（系统截图）、PNG，或「文件路径」而不是像素。浏览器复制经常是「文本 + 图」同时存在，必须优先图。

处理顺序：

1. File Action / argv 已给出本地路径，直接用（多个只取第一个并提示）
2. 否则 `osascript`：本地 `file URL`（且是图片文件）→ `«class PNGf»` → `TIFF picture`
3. TIFF 用 `sips -s format png` 转成 PNG 再上传
4. 临时文件放 `$TMPDIR`，名字带时间戳和 pid，结束时删除
5. 没有图片时立刻退出，不要对文本 URL 误上传

不要用 `pbpaste`。不要把 Homebrew `pngpaste` 当硬依赖。系统自带 `osascript` + `sips` + `curl`。

MIME 必须带上（`image/png`、`image/jpeg`、`image/gif`、`image/webp`）。

## 6. 上传脚本契约

`src/upload.py`：解析来源 → POST → 成功才写剪贴板并通知。

```text
环境变量（与 Configuration 同名）
  imgbed_url, auth_code, upload_channel

调用
  /usr/bin/python3 src/upload.py /path/to/image.png
  /usr/bin/python3 src/upload.py            # 读剪贴板
  /usr/bin/python3 src/upload.py --test     # 上传 1×1 PNG 测连接

stdout  成功时一行 URL（给 Debugger 看）
stderr  人读错误
exit 0  成功；非 0 失败
成功    pbcopy URL（无尾换行）+ osascript 通知（文件名 + URL）
失败    不调用 pbcopy
```

请求形态：

```http
POST /upload?returnFormat=full&uploadChannel=cfr2&autoRetry=false
authCode: <password>
Content-Type: multipart/form-data

file=@screenshot.png;type=image/png
```

校验：

- URL 必须是 `https://`，去掉尾斜杠；用户写成带 `/upload` 时归一成 origin 再拼 `/upload`
- 此实例认证码必填；空认证码收到 401 时提示去 Workflow 配置填写
- 只接受 `png/jpg/jpeg/gif/webp`；`tif/tiff` 先转 PNG
- 超时 30s
- 解析响应必须是 JSON 数组（或 `responseFormat=object` 的单对象）且含 `src`

`imgbed-test` **不要**打 `/api/auth/sessionCheck`。那个接口只检查 Cookie 会话，失败也返回 HTTP 200，测不了认证码。

## 7. 配置与安全

- `auth_code` 只存在 Alfred 的 workflow 配置 / `prefs.plist`，不要写进 `info.plist` 默认值，不要提交
- 认证码 = ImgBed 后台「用户认证码」，不是管理员密码
- README 说明：Alfred → Workflows → 本 workflow 右侧 `[x]` 配置
- bundle id：`com.qydxyx.alfred-imgbed`
- `/usr/bin/python3` 需要 Xcode Command Line Tools（没装时会弹安装框）

## 8. 分阶段

### 阶段 0：手工打通接口

```bash
curl -sS -F "file=@/path/to/test.png" \
  -H "authCode: YOUR_CODE" \
  "https://cloudflare-imgbed.qydxyx.workers.dev/upload?returnFormat=full&uploadChannel=cfr2&autoRetry=false"
```

确认返回 `[{"src":"https://.../file/..."}]`。这一步不过，后面 Alfred 白做。无认证时现网返回 `401 Unauthorized`。

### 阶段 1：脚本 + File Action

- 仓库、`info.plist`、Configuration、icon
- File Action 接受图片文件
- Python 上传、成功才复制、失败通知
- 用一张本地 PNG 跑通（命令行先跑，再在 Alfred 里跑）

### 阶段 2：剪贴板

- Hotkey 无参数；Keyword `imgbed`
- TIFF → PNG；file URL；无图；401
- `imgbed-test` 用 1×1 PNG 测连接

### 阶段 3：打磨

- README：安装、配置、快捷键、常见错误
- 导出 `.alfredworkflow`，认证码留空

## 9. 验收标准

- Finder 选中 PNG，File Action 上传成功，剪贴板是 `https://cloudflare-imgbed.qydxyx.workers.dev/file/...`
- `⌘⌃⇧4` 复制到剪贴板后，Hotkey / `imgbed` 能上传（TIFF 已转 PNG）
- `⌘⇧4` 存到桌面的文件，选中后 File Action 能上传
- 改 Configuration 里的 URL、认证码后立即生效
- 认证码错误 → 通知 `401 Unauthorized`，系统剪贴板内容不变
- 剪贴板是文字 → 提示「剪贴板里没有图片」，剪贴板不变
- `imgbed-test` 认证码正确 → 通知连接成功；错误 → 401，剪贴板不变

## 10. 实现要点

- `/usr/bin/python3` + `/usr/bin/curl` + `/usr/bin/sips` + `osascript`，不依赖 `requests` / Homebrew
- Alfred 传参用 argv，不要拼进 shell；路径可含空格和中文
- 多个路径只取第一个
- 成功通知同时显示短文件名和 URL
- Python `print` 带换行只用于 stdout 日志，写入剪贴板时用 `pbcopy` 且不含尾换行

## 11. 后续可选项（不做进 v1）

- 多 profile
- 上传后可选 Markdown `![](url)` 或 HTML `<img>`
- `uploadFolder=alfred/` 目录隔离
- API Token 替代认证码
- 历史记录 Script Filter
- HEIC 自动转 PNG
