# -*- coding: utf-8 -*-
"""
中国时区时间工具
"""
from datetime import date, datetime, time, timedelta, timezone


CHINA_TZ = timezone(timedelta(hours=8), name="UTC+8")


def get_china_now() -> datetime:
    """返回中国时区当前时间（UTC+8），并统一转成无时区 datetime 便于现有 DB 使用。"""
    return datetime.now(timezone.utc).astimezone(CHINA_TZ).replace(tzinfo=None)


def get_china_date() -> date:
    """返回中国时区当前日期。"""
    return get_china_now().date()


def get_china_today_str() -> str:
    """返回中国时区今天日期字符串。"""
    return get_china_now().strftime("%Y-%m-%d")


def get_china_timestamp_ms() -> int:
    """返回当前毫秒级时间戳。"""
    return int(datetime.now(timezone.utc).astimezone(CHINA_TZ).timestamp() * 1000)


def get_china_day_start(target_date: date = None) -> datetime:
    """返回中国时区某天的 00:00:00。"""
    return datetime.combine(target_date or get_china_date(), time.min)
