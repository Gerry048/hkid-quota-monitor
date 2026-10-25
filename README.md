# 香港身份证预约配额监控

在 Mac 上查询香港入境事务处**公开**的人事登记办事处预约配额。你设定的日期和办事处一旦出现名额，脚本会：

1. 播放系统提示音
2. 弹出 macOS 通知
3. 用 Safari 打开官方「更改预约」入口
4. 可选：通过 [Bark](https://apps.apple.com/app/bark-customed-notifications/id1403753865) 或 [ntfy](https://apps.apple.com/app/ntfy/id1625396347) 推到 iPhone

名额还在时，会按间隔反复提醒，不会推送一次就停。在终端按 `Control-C` 才会停止。

脚本**不会**绕过官网的人机验证，**不会**填写身份证号码、出生日期或查询编号，也**不会**替你提交预约。收到提醒后，请自己在 Safari 里完成验证、登录和更改日期。

## 环境

- macOS（通知、提示音和自动打开 Safari 都依赖 macOS）
- 系统自带的 `python3`（3.9 或更新）和 `curl`
- 不需要安装第三方 Python 包

iPhone 推送是可选的。只在 Mac 前盯着的话，可以不配置 Bark / ntfy。

## 下载

```bash
git clone https://github.com/Gerry048/hkid-quota-monitor.git
cd hkid-quota-monitor
```

## 第一次使用

先改成你自己要的日期。脚本自带的默认区间是 **2026-08-25 至 2026-10-01（含两端）**，过了这个区间就不会有匹配结果。

只查一次，确认网络和参数没问题：

```bash
python3 hkid_quota_monitor.py --once --after 2026-11-01 --before 2026-12-31
```

终端会打印类似：

```text
[2026-10-25 22:30:00 HKT] 开始监控 ...
[2026-10-25 22:30:01 HKT] 暂未发现目标日期内的名额
```

确认正常后，去掉 `--once`，让它一直跑。保持这个终端窗口开着：

```bash
python3 hkid_quota_monitor.py --after 2026-11-01 --before 2026-12-31
```

## 参数

| 参数 | 默认 | 作用 |
| --- | --- | --- |
| `--after` | `2026-08-25` | 只提醒这一天及之后的名额，格式 `YYYY-MM-DD` |
| `--before` | `2026-10-01` | 只提醒这一天及之前的名额，格式 `YYYY-MM-DD` |
| `--offices` | `all` | 办事处代码，逗号分隔。见下表 |
| `--interval` | `600` | 两次查询之间的秒数。小于 2 会按 2 秒处理 |
| `--once` | 关 | 只查一次就退出 |
| `--no-open` | 关 | 发现名额时不自动打开 Safari |
| `--bark` | 读 `bark.key` 或环境变量 | iPhone Bark 推送，见下文 |
| `--ntfy` | 读 `ntfy.topic` 或环境变量 | iPhone ntfy 推送，见下文 |
| `--test-notify` | 关 | 发一条测试提醒后退出，不查询名额 |

日期是闭区间：`--after` 和 `--before` 当天都算在内。`--after` 不能晚于 `--before`。

官网这份公开预览大约每 15 分钟更新一次。默认 600 秒（10 分钟）已经够用，把间隔改得很短通常看不到更新的数据，也没有必要。

### 办事处

| 代码 | 办事处 |
| --- | --- |
| `RHK` | 港岛（湾仔） |
| `RKO` | 九龙（长沙湾） |
| `RTK` | 将军澳 |
| `FTO` | 火炭 |
| `TMO` | 屯门 |
| `YLO` | 元朗 |

只看港岛和九龙：

```bash
python3 hkid_quota_monitor.py --offices RHK,RKO --after 2026-11-01 --before 2026-12-31
```

六个办事处一起看（默认）：

```bash
python3 hkid_quota_monitor.py --offices all --after 2026-11-01 --before 2026-12-31
```

发现名额但只想要通知、不要弹出 Safari：

```bash
python3 hkid_quota_monitor.py --no-open --after 2026-11-01 --before 2026-12-31
```

## 推送到 iPhone：Bark

Mac 通知不会自动出现在 iPhone 上。Bark 免费，点开通知会进入官方更改预约页。

### 1. 安装并复制 Key

1. 在 iPhone 的 App Store 安装 [Bark](https://apps.apple.com/app/bark-customed-notifications/id1403753865)。
2. 打开 App，允许通知。
3. 复制设备 Key。页面上经常是一整条地址，例如 `https://api.day.app/xxxxxxxx/`。`xxxxxxxx` 那一段就是 Key，整条地址也可以。

Key 相当于这台手机的推送地址。不要发到聊天软件里，也不要提交到 Git。

### 2. 保存 Key

在脚本同一目录新建 `bark.key`，一行一个 Key。`#` 开头的行是备注：

```text
# 自己
xxxxxxxx
# 家人
yyyyyyyy
```

也可以不建文件，改用环境变量（多个 Key 用逗号或换行分隔）：

```bash
export HKID_BARK_KEY="xxxxxxxx"
```

或每次在命令里写：

```bash
python3 hkid_quota_monitor.py --bark xxxxxxxx --test-notify
```

`--bark` 后面不跟内容时，仍会读取 `bark.key` 和环境变量 `HKID_BARK_KEY`。

### 3. 测试

```bash
python3 hkid_quota_monitor.py --test-notify
```

iPhone 应马上收到标题为「香港身份证预约有名额」的通知。Mac 也会响一声并弹出通知，但这次**不会**打开 Safari。

收不到时检查：

- `bark.key` 和脚本在同一目录，Key 没有多余空格
- iPhone 已允许 Bark 通知
- 没有被专注模式静音

### 4. 开始监控

```bash
python3 hkid_quota_monitor.py --after 2026-11-01 --before 2026-12-31
```

有名额时，已配置的每一台 Bark 设备都会收到推送。某一台失败不会影响其他设备，终端里会写出失败原因。

## 备选：ntfy

不想用 Bark 时，安装 [ntfy](https://apps.apple.com/app/ntfy/id1625396347)，自己起一个不容易猜到的主题名，例如 `hkid-yourname-随机字符`。主题名知道的人都能往里发消息，不要用 `hkid` 这种短名字。

在 App 里订阅这个主题，然后：

```bash
python3 hkid_quota_monitor.py --ntfy hkid-yourname-随机字符 --test-notify
```

想每次都自动带上，把主题名单独写进同目录的 `ntfy.topic`（文件里只有这一行），或：

```bash
export HKID_NTFY_TOPIC="hkid-yourname-随机字符"
```

Bark 和 ntfy 可以同时开。两个都没配置时，仍然会提醒这台 Mac。

## 让它在后台一直跑

终端关掉之后，普通方式启动的脚本会一起停。如果希望登录 macOS 后自动开始，可以用「登录项」里的启动代理。下面的例子请改成你的真实路径和日期。

保存为 `~/Library/LaunchAgents/local.hkid-quota-monitor.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>local.hkid-quota-monitor</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/你的用户名/hkid-quota-monitor/hkid_quota_monitor.py</string>
    <string>--after</string>
    <string>2026-11-01</string>
    <string>--before</string>
    <string>2026-12-31</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/你的用户名/hkid-quota-monitor</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/hkid-quota-monitor.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/hkid-quota-monitor.err</string>
</dict>
</plist>
```

`WorkingDirectory` 要指向放了 `bark.key` 的那个目录，否则后台运行时读不到 Key。

加载、停止、卸载：

```bash
launchctl load ~/Library/LaunchAgents/local.hkid-quota-monitor.plist
launchctl unload ~/Library/LaunchAgents/local.hkid-quota-monitor.plist
tail -f /tmp/hkid-quota-monitor.log
```

第一次请先在终端里用 `--test-notify` 和 `--once` 确认能跑，再交给 launchd。系统如果弹出「允许通知」，选允许。

## 看到名额之后

通知里的日期和办事处只说明公开预览里出现了名额，不代表一定还能订到。请立刻打开 Safari 里的官方页面（通知点击 Bark / ntfy 也会打开同一页）：

[更改预约入口](https://entry.es2.immd.gov.hk/surgecontrol_extend/ticket/getTicketGet?svcId=57A&language=zh&country=HK)

页面上的蓝色验证需要你自己完成。脚本到这一步就结束了。

## 常见问题

**终端写「暂未发现目标日期内的名额」。**  
日期区间、办事处可能设窄了，或者当前预览里确实没有位。用 `--once` 看最近一条日志。默认日期如果已经过去，请改 `--after` 和 `--before`。

**终端写「查询失败，将稍后重试」。**  
多半是网络或官网暂时打不开。脚本会按间隔继续，不用重启。

**参数错误，程序直接退出。**  
日期要写成 `2026-11-01` 这种格式；办事处只能是上表里的代码；起始日不能晚于结束日。

**测试推送成功，但真实名额没有推到手机。**  
确认这次启动的命令能读到同一个 `bark.key`，并且终端启动日志里有 `iPhone 推送：Bark`。日志如果是「未配置 iPhone 推送」，说明 Key 没被读到。

**可以放到 Windows 或 Linux 上吗？**  
查询本身只用了 `curl`。通知、声音和自动打开 Safari 是 macOS 专用的。其他系统上即使查到名额，也完成不了这三步。

## 隐私

仓库和脚本里没有身份证资料，也没有推送 Key。`bark.key`、`ntfy.topic` 和 `.env` 已在 `.gitignore` 里。克隆之后在自己电脑上创建这些文件即可。
