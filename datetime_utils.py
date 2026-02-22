#!/usr/bin/env python3
"""
Datetime utilities for consistent timezone handling across the codebase.

All timestamps should be:
1. Stored in UTC
2. Include timezone info
3. Use ISO 8601 format for serialization
"""
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    Get current time in UTC with timezone info.

    Returns:
        datetime: Current UTC time with timezone
    """
    return datetime.now(timezone.utc)


def utc_timestamp() -> str:
    """
    Get current UTC timestamp as ISO 8601 string.

    Returns:
        str: ISO 8601 timestamp (e.g., "2026-02-22T15:30:45.123456+00:00")
    """
    return utc_now().isoformat()


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """
    Parse ISO 8601 timestamp string to datetime.

    Handles:
    - Timestamps with 'Z' suffix (converts to +00:00)
    - Timestamps with timezone offset
    - Timestamps without timezone (assumes UTC)

    Args:
        timestamp_str: ISO 8601 timestamp string

    Returns:
        datetime: Parsed datetime with UTC timezone

    Examples:
        >>> parse_iso_timestamp("2026-02-22T15:30:45Z")
        >>> parse_iso_timestamp("2026-02-22T15:30:45+00:00")
        >>> parse_iso_timestamp("2026-02-22T15:30:45")
    """
    # Replace 'Z' with '+00:00' for Python's fromisoformat
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1] + '+00:00'

    try:
        dt = datetime.fromisoformat(timestamp_str)
    except ValueError:
        # No timezone info, assume UTC
        dt = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)

    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt


def to_iso_string(dt: datetime) -> str:
    """
    Convert datetime to ISO 8601 string in UTC.

    Args:
        dt: datetime object (with or without timezone)

    Returns:
        str: ISO 8601 timestamp in UTC
    """
    # Convert to UTC if not already
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.isoformat()


def seconds_since(timestamp: datetime) -> float:
    """
    Calculate seconds elapsed since given timestamp.

    Args:
        timestamp: Past datetime (UTC)

    Returns:
        float: Seconds elapsed
    """
    now = utc_now()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    return (now - timestamp).total_seconds()


def is_expired(timestamp: datetime, ttl_seconds: int) -> bool:
    """
    Check if timestamp has expired based on TTL.

    Args:
        timestamp: Datetime to check
        ttl_seconds: Time-to-live in seconds

    Returns:
        bool: True if expired
    """
    return seconds_since(timestamp) > ttl_seconds


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        str: Human-readable duration (e.g., "2h 30m", "45s")
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = seconds / 60
        return f"{mins:.0f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        mins = (seconds % 3600) / 60
        return f"{hours:.0f}h {mins:.0f}m"
    else:
        days = seconds / 86400
        hours = (seconds % 86400) / 3600
        return f"{days:.0f}d {hours:.0f}h"


# Example usage
if __name__ == '__main__':
    print("=" * 80)
    print("Datetime Utilities - Test")
    print("=" * 80)
    print()

    # Current time
    now = utc_now()
    print(f"Current UTC time: {now}")
    print(f"ISO timestamp: {utc_timestamp()}")
    print()

    # Parsing
    test_timestamps = [
        "2026-02-22T15:30:45Z",
        "2026-02-22T15:30:45+00:00",
        "2026-02-22T15:30:45",
        "2026-02-22T10:30:45-05:00",  # EST -> UTC conversion
    ]

    print("Parsing test:")
    for ts in test_timestamps:
        parsed = parse_iso_timestamp(ts)
        print(f"  {ts:40} -> {parsed}")
    print()

    # Duration formatting
    print("Duration formatting:")
    for secs in [30, 90, 3600, 7200, 90000]:
        print(f"  {secs:6} seconds -> {format_duration(secs)}")
    print()

    print("✅ Datetime utilities test complete")
