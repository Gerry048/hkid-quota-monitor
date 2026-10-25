#!/usr/bin/env python3
"""Monitor Hong Kong Immigration Department HKID appointment quota.

Uses the public quota preview endpoint. When an appointment in the target
date range appears, it sends a macOS notification, sounds an alert, and opens
the official change-booking entry page in Safari. Optional Bark / ntfy push
can also alert an iPhone.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


QUOTA_URL = (
    "https://eservices.es2.immd.gov.hk/surgecontrolgate/ticket/"
    "getSituation?svcId=579"
)
CHANGE_URL = (
    "https://entry.es2.immd.gov.hk/surgecontrol_extend/ticket/"
    "getTicketGet?svcId=57A&language=zh&country=HK"
)
OFFICE_NAMES = {
    "RHK": "港岛（湾仔）",
    "RKO": "九龙（长沙湾）",
    "RTK": "将军澳",
    "FTO": "火炭",
    "TMO": "屯门",
    "YLO": "元朗",
}
FULL_GENERAL = "quota-r"
NO_EXTENDED = "no-quotaK"
NOTIFY_TITLE = "香港身份证预约有名额"


def load_local_secret(env_name: str, filename: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    try:
        return (SCRIPT_DIR / filename).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def parse_bark_keys(raw: str) -> list[str]:
    """One key per line in bark.key. Commas also work. Lines starting with # are ignored."""
    keys: list[str] = []
    seen: set[str] = set()
    for line in raw.replace(",", "\n").splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        if item in seen:
            continue
        seen.add(item)
        keys.append(item)
    return keys


def parse_args() -> argparse.Namespace:
    bark_default = load_local_secret("HKID_BARK_KEY", "bark.key")
    ntfy_default = load_local_secret("HKID_NTFY_TOPIC", "ntfy.topic")
    parser = argparse.ArgumentParser(description="监控香港身份证预约配额")
    parser.add_argument(
        "--after",
        default="2026-08-25",
        help="只提醒此日期及之后的名额，格式 YYYY-MM-DD（默认：2026-08-25）",
    )
    parser.add_argument(
        "--before",
        default="2026-10-01",
        help="只提醒此日期及之前的名额，格式 YYYY-MM-DD（默认：2026-10-01）",
    )
    parser.add_argument(
        "--offices",
        default="all",
        help="办事处代码，逗号分隔；默认 all。可选：RHK,RKO,RTK,FTO,TMO,YLO",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=600,
        help="查询间隔秒数（最低 600，官网数据每 15 分钟更新）",
    )
    parser.add_argument(
        "--once", action="store_true", help="只查询一次，不持续监控"
    )
    parser.add_argument(
        "--no-open", action="store_true", help="发现名额时不自动打开 Safari"
    )
    parser.add_argument(
        "--bark",
        nargs="?",
        const=bark_default,
        default=bark_default,
        help="Bark 设备 Key（可多行/逗号分隔）。默认同目录 bark.key 或环境变量 HKID_BARK_KEY",
    )
    parser.add_argument(
        "--ntfy",
        nargs="?",
        const=ntfy_default,
        default=ntfy_default,
        help="ntfy 主题名。默认同目录 ntfy.topic 或环境变量 HKID_NTFY_TOPIC",
    )
    parser.add_argument(
        "--test-notify",
        action="store_true",
        help="发送一条测试提醒（Mac + iPhone）后退出",
    )
    return parser.parse_args()


def selected_offices(raw: str) -> set[str]:
    if raw.strip().lower() == "all":
        return set(OFFICE_NAMES)
    values = {item.strip().upper() for item in raw.split(",") if item.strip()}
    unknown = values - set(OFFICE_NAMES)
    if unknown:
        raise ValueError(f"未知办事处代码：{', '.join(sorted(unknown))}")
    if not values:
        raise ValueError("至少选择一个办事处")
    return values


def fetch_quota() -> dict:
    result = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "30",
            "--header",
            "Accept: application/json",
            "--user-agent",
            "HKID-Quota-Monitor/1.0 (personal-use; 15-minute interval)",
            QUOTA_URL,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def parse_hk_date(value: str) -> date:
    return datetime.strptime(value, "%m/%d/%Y").date()


def find_slots(
    payload: dict, start: date, end: date, offices: set[str]
) -> list[dict]:
    matches = []
    for row in payload.get("data", []):
        office = row.get("officeId")
        if office not in offices:
            continue
        slot_date = parse_hk_date(row["date"])
        if slot_date < start or slot_date > end:
            continue
        general_available = row.get("quotaR") != FULL_GENERAL
        extended_available = row.get("quotaK") != NO_EXTENDED
        if general_available or extended_available:
            matches.append(
                {
                    "date": slot_date,
                    "office": office,
                    "general": general_available,
                    "extended": extended_available,
                }
            )
    return sorted(matches, key=lambda item: (item["date"], item["office"]))


def post_json(url: str, payload: dict) -> None:
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--max-time",
            "15",
            "-X",
            "POST",
            "--header",
            "Content-Type: application/json; charset=utf-8",
            "--data-binary",
            json.dumps(payload, ensure_ascii=False),
            "--write-out",
            "\n%{http_code}",
            url,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "请求失败").strip())
    body, _, status = result.stdout.rpartition("\n")
    if not status.startswith("2"):
        message = body.strip() or f"HTTP {status}"
        try:
            parsed = json.loads(body)
            message = str(parsed.get("message") or parsed.get("error") or message)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(message)


def bark_endpoint(raw: str) -> str:
    value = raw.strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value.rstrip("/")
    return f"https://api.day.app/{value}"


def push_bark(raw: str, title: str, body: str) -> None:
    post_json(
        bark_endpoint(raw),
        {
            "title": title,
            "body": body,
            "sound": "alarm",
            "call": "0",
            "level": "active",
            "volume": 2,
            "group": "HKID",
            "url": CHANGE_URL,
        },
    )


def push_ntfy(topic: str, title: str, body: str) -> None:
    topic = topic.strip()
    post_json(
        "https://ntfy.sh",
        {
            "topic": topic,
            "title": title,
            "message": body,
            "priority": 5,
            "tags": ["rotating_light"],
            "click": CHANGE_URL,
        },
    )


def notify_mac(message: str, open_safari: bool) -> None:
    safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        f'display notification "{safe_message}" '
        f'with title "{NOTIFY_TITLE}" sound name "Glass"'
    )
    subprocess.run(["osascript", "-e", script], check=False)
    subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
    if open_safari:
        subprocess.run(["open", "-a", "Safari", CHANGE_URL], check=False)


def notify(
    message: str,
    open_safari: bool,
    bark: str,
    ntfy: str,
) -> None:
    notify_mac(message, open_safari)
    keys = parse_bark_keys(bark)
    ok = 0
    for index, key in enumerate(keys, start=1):
        try:
            push_bark(key, NOTIFY_TITLE, message)
            ok += 1
        except RuntimeError as exc:
            log(f"Bark 推送失败（{index}/{len(keys)}）：{exc}")
    if ok:
        log(f"已推送到 {ok}/{len(keys)} 台 iPhone（Bark）")
    if ntfy.strip():
        try:
            push_ntfy(ntfy, NOTIFY_TITLE, message)
            log("已推送到 iPhone（ntfy）")
        except RuntimeError as exc:
            log(f"ntfy 推送失败：{exc}")


def log(message: str) -> None:
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"[{stamp}] {message}", flush=True)


def iphone_status(bark: str, ntfy: str) -> str:
    channels = []
    bark_count = len(parse_bark_keys(bark))
    if bark_count:
        channels.append(f"Bark × {bark_count}" if bark_count > 1 else "Bark")
    if ntfy.strip():
        channels.append("ntfy")
    if channels:
        return "iPhone 推送：" + "、".join(channels)
    return "未配置 iPhone 推送（可用 --bark 或 --ntfy）"


def main() -> int:
    args = parse_args()
    try:
        start = date.fromisoformat(args.after)
        end = date.fromisoformat(args.before)
        if start > end:
            raise ValueError("起始日期不能晚于结束日期")
        offices = selected_offices(args.offices)
    except ValueError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return 2

    if args.test_notify:
        log("发送测试提醒")
        notify(
            "这是测试：脚本可以提醒这台 Mac 和 iPhone。点开可进入更改预约页。",
            open_safari=False,
            bark=args.bark,
            ntfy=args.ntfy,
        )
        log(iphone_status(args.bark, args.ntfy))
        return 0

    interval = max(args.interval, 2)
    log(
        f"开始监控 {', '.join(OFFICE_NAMES[o] for o in sorted(offices))}；"
        f"目标日期 {start.isoformat()} 至 {end.isoformat()}（含）；间隔 {interval} 秒；"
        f"{iphone_status(args.bark, args.ntfy)}"
    )

    while True:
        try:
            slots = find_slots(fetch_quota(), start, end, offices)
            if slots:
                summary = "；".join(
                    f"{item['date'].strftime('%m-%d')} {OFFICE_NAMES[item['office']]}"
                    for item in slots[:6]
                )
                if len(slots) > 6:
                    summary += f"；另有 {len(slots) - 6} 个"
                log(f"发现名额：{summary}")
                notify(
                    summary,
                    open_safari=not args.no_open,
                    bark=args.bark,
                    ntfy=args.ntfy,
                )
            else:
                log("暂未发现目标日期内的名额")
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as exc:
            log(f"查询失败，将稍后重试：{exc}")

        if args.once:
            return 0
        log(f"{interval} 秒后再次查询，监控继续")
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            log("已停止")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
