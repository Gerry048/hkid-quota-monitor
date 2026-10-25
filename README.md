# 香港身份证预约配额监控

监控香港入境事务处公开的「人事登记办事处预约配额预览」。目标日期出现名额时，在 Mac 上响铃并弹出通知，用 Safari 打开官方更改预约页，也可以推送到 iPhone。

脚本只读取公开预览、只负责提醒。它不会填写身份资料，不会绕过验证码，也不会替你提交预约。

## 环境

- macOS（通知、提示音和自动打开 Safari 都依赖系统命令）
- 系统自带的 `python3`（3.9 或更新）和 `curl`
- 可选：iPhone 上的 [Bark](https://apps.apple.com/app/bark-customed-notifications/id1403753865) 或 [ntfy](https://apps.apple.com/app/ntfy/id1625396347)

不需要安装第三方 Python 包。

## 获取代码

```bash
git clone https://github.com/Gerry048/hkid-quota-monitor.git
cd hkid-quota-monitor
```

如果这台 Mac 上已经有脚本，直接在所在目录运行即可，不必再克隆一份。

## 第一次使用

先查一次，确认网络和日期参数都正常。这一步不会打开浏览器，也不会持续运行：

```bash
python3 hkid_quota_monitor.py --once --after 2026-11-01 --before 2026-12-31
```

终端会打印两种结果之一：

- `发现名额：...`：目标范围内已经有可预约时段
- `暂未发现目标日期内的名额`：当前预览里没有符合条件的时段

日期请改成自己要的范围。`--after` 和 `--before` 都包含当天，格式是 `YYYY-MM-DD`。脚本自带的默认范围是 `2026-08-25` 至 `2026-10-01`，那只是示例，开始监控前请换成你自己的日期。

确认查询正常后，开始持续监控：

```bash
python3 hkid_quota_monitor.py --after 2026-11-01 --before 2026-12-31
```

保持这个终端窗口开着。按 `Control-C` 停止。

只要名额还在，脚本会按间隔反复提醒，不会响一次就停。名额消失后，它继续查询，之后再出现会再次提醒。

## 它会做什么

发现符合条件的名额时，依次：

1. 在终端打印办事处和日期
2. 播放 macOS 提示音，并弹出标题为「香港身份证预约有名额」的通知
3. 用 Safari 打开入境处「更改预约」入口
4. 如果配置了 Bark 或 ntfy，同时推到 iPhone；点开推送也会进入同一个更改预约页

更改预约页有人机验证。收到提醒后，请自己完成验证、登录，再改期并提交。

## 参数

```bash
python3 hkid_quota_monitor.py \
  --after 2026-11-01 \
  --before 2026-12-31 \
  --offices RHK,RKO \
  --interval 600
```

| 参数 | 默认 | 作用 |
| --- | --- | --- |
| `--after` | `2026-08-25` | 只提醒这一天及之后的名额 |
| `--before` | `2026-10-01` | 只提醒这一天及之前的名额 |
| `--offices` | `all` | 办事处代码，逗号分隔。`all` 表示全部 |
| `--interval` | `600` | 查询间隔，单位秒。小于 2 秒时按 2 秒执行 |
| `--once` | 关闭 | 只查询一次，然后退出 |
| `--no-open` | 关闭 | 发现名额时不打开 Safari |
| `--bark` | 见下文 | iPhone Bark 推送 |
| `--ntfy` | 见下文 | iPhone ntfy 推送 |
| `--test-notify` | 关闭 | 发一条测试提醒后退出，不打开 Safari |

起始日期不能晚于结束日期。办事处代码写错时，脚本会直接退出并指出未知代码。

公开预览大约每 15 分钟更新一次，所以默认 600 秒足够。把间隔改得很短，通常也不会更早看到新名额。

只看港岛和九龙：

```bash
python3 hkid_quota_monitor.py --offices RHK,RKO --after 2026-11-01 --before 2026-12-31
```

发现名额时只通知、不打开浏览器：

```bash
python3 hkid_quota_monitor.py --no-open --after 2026-11-01 --before 2026-12-31
```

## 办事处代码

| 代码 | 办事处 |
| --- | --- |
| `RHK` | 港岛（湾仔） |
| `RKO` | 九龙（长沙湾） |
| `RTK` | 将军澳 |
| `FTO` | 火炭 |
| `TMO` | 屯门 |
| `YLO` | 元朗 |

## 怎样算「有名额」

预览里每个办事处、每一天有两类时段：

- 普通时段有余量
- 延长时段有余量

两类里任意一类可用，就会提醒。同一轮里如果有多个日期或办事处，通知里最多列出 6 条，其余用「另有 N 个」概括。

## 推送到 iPhone

Mac 通知不会自动出现在 iPhone 上。需要 Bark 或 ntfy 其中一种。两种可以同时开。

### Bark

1. 在 iPhone 的 App Store 安装 Bark，打开 App，允许通知。
2. 复制设备 Key。页面上经常是一整条地址，例如 `https://api.day.app/你的Key/`。脚本接受完整地址，也接受其中那段 Key。
3. 在脚本同目录新建 `bark.key`，一行一个 Key。`#` 开头的行是备注：

```text
# 自己
你的Key
# 家人
另一台手机的Key
```

4. 先发测试，不要直接进入长时间监控：

```bash
python3 hkid_quota_monitor.py --test-notify
```

iPhone 应马上收到「香港身份证预约有名额」。终端会写 `已推送到 1/1 台 iPhone（Bark）`。没收到时，检查 App 的通知权限，以及专注模式有没有把 Bark 静音。

5. 测试通过后再开始监控。只要 `bark.key` 在同目录，不用每次加参数：

```bash
python3 hkid_quota_monitor.py --after 2026-11-01 --before 2026-12-31
```

也可以不写文件，临时传入，多个 Key 用逗号分隔：

```bash
python3 hkid_quota_monitor.py --bark "你的Key,另一台手机的Key" --test-notify
```

`bark.key` 等于手机的推送凭证。不要发给别人，不要提交到 Git。仓库里的 `.gitignore` 已经忽略 `bark.key`、`*.key`、`ntfy.topic` 和 `.env`。

### ntfy

1. 在 iPhone 安装 ntfy。
2. 自己编一个不容易猜到的主题名，例如 `hkid-你的名字-一串随机字符`。谁知道这个名字，谁就能给你的手机发通知，也能看到发到这个主题的内容。
3. 在 ntfy App 里订阅同一个主题名。
4. 测试：

```bash
python3 hkid_quota_monitor.py --ntfy "hkid-你的名字-一串随机字符" --test-notify
```

主题名也可以写在同目录的 `ntfy.topic` 文件里，或放进环境变量，这样日常运行不用把名字写在命令里。

### 环境变量

环境变量优先于同目录的密钥文件：

```bash
export HKID_BARK_KEY="你的Key"
export HKID_NTFY_TOPIC="hkid-你的名字-一串随机字符"
python3 hkid_quota_monitor.py --test-notify
```

## 登录后自动运行

用 macOS 的 `launchd` 可以在登录后启动监控，终端关掉也会继续跑。把下面保存为 `~/Library/LaunchAgents/hkid-quota-monitor.plist`，并把脚本路径和日期改成你的：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>hkid-quota-monitor</string>
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

`WorkingDirectory` 要指到放着 `bark.key` 的目录，否则登录后自动运行时会找不到 Key。

加载、查看日志、停止：

```bash
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/hkid-quota-monitor.plist
tail -f /tmp/hkid-quota-monitor.log
launchctl bootout gui/$UID ~/Library/LaunchAgents/hkid-quota-monitor.plist
```

改过 plist 之后，先 `bootout` 再 `bootstrap` 一次。

## 常见情况

**终端写着查询失败。**  
多半是网络或入境处页面暂时打不开。脚本会记下错误，等下一个间隔再查，不会退出。

**一直显示没有名额。**  
先核对 `--after`、`--before` 和 `--offices`。预览本身大约 15 分钟才更新一次，刚放出来的名额也可能要等下一轮才出现在接口里。

**Mac 没有弹出通知。**  
到「系统设置 → 通知」，允许终端（或实际运行脚本的 App）显示通知。专注模式也可能把通知挡住。可以先跑 `--test-notify`。

**iPhone 没收到，Mac 有。**  
看终端有没有 `Bark 推送失败` 或 `ntfy 推送失败`。Key 或主题名不对时，监控仍会继续，只是手机那一路失败。

**Safari 打开了但过不了蓝色验证页。**  
这是入境处网站自己的验证。脚本不会代点，也不会保存身份证号码、出生日期或查询编号。

## 隐私

查询使用入境处公开的配额预览地址，请求里带有说明用途的 User-Agent，默认大约每 10 分钟访问一次。

Bark Key 和 ntfy 主题名只留在你自己的电脑上。这个仓库不包含、也不应该包含这些凭证。

## 许可

[MIT](LICENSE)
