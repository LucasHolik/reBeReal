"""Parser for the `posts.json` shape shipped in the 2026-05-18 BeReal export."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from rebereal.models import Post

log = logging.getLogger(__name__)


class PostsJsonParser:
    """Parses a `posts.json` file into a stream of `Post` objects.

    Defensive against missing optional fields. Records that lack required
    fields are logged and skipped rather than raising — a single malformed
    entry should not abort a 1,200-post run.
    """

    def parse(self, path: Path) -> Iterator[Post]:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        if not isinstance(raw, list):
            raise ValueError(f"{path}: expected top-level JSON array, got {type(raw).__name__}")

        for index, entry in enumerate(raw):
            post = self._parse_entry(entry, index)
            if post is not None:
                yield post

    def _parse_entry(self, entry: Any, index: int) -> Post | None:
        if not isinstance(entry, dict):
            log.warning("entry #%d: not an object, skipping", index)
            return None

        primary = entry.get("primary")
        secondary = entry.get("secondary")
        taken_at_raw = entry.get("takenAt")

        if not isinstance(primary, dict) or "path" not in primary:
            log.warning("entry #%d: missing primary.path, skipping", index)
            return None
        if not isinstance(secondary, dict) or "path" not in secondary:
            log.warning("entry #%d: missing secondary.path, skipping", index)
            return None
        if not isinstance(taken_at_raw, str):
            log.warning("entry #%d: missing/invalid takenAt, skipping", index)
            return None

        try:
            taken_at = _parse_iso8601_utc(taken_at_raw)
        except ValueError as e:
            log.warning("entry #%d: invalid takenAt %r (%s), skipping", index, taken_at_raw, e)
            return None

        caption = entry.get("caption")
        if caption is not None and not isinstance(caption, str):
            caption = None

        location = _parse_location(entry.get("location"))

        retake_raw = entry.get("retakeCounter", 0)
        try:
            retake_counter = int(retake_raw) if retake_raw is not None else 0
        except (TypeError, ValueError):
            retake_counter = 0

        return Post(
            taken_at=taken_at,
            back_path=primary["path"],
            front_path=secondary["path"],
            caption=caption if caption else None,
            location=location,
            retake_counter=retake_counter,
        )


def _parse_iso8601_utc(value: str) -> datetime:
    """Parse `2022-07-08T09:33:33.729Z` into a tz-aware UTC datetime."""
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_location(raw: Any) -> tuple[float, float] | None:
    if not isinstance(raw, dict):
        return None
    lat = raw.get("latitude")
    lon = raw.get("longitude")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return None
    return (float(lat), float(lon))
