"""Tests for the posts.json parser — fixture-based, no real photos required."""

from __future__ import annotations

from datetime import timezone
from pathlib import Path

from rebereal.parsers.posts_json import PostsJsonParser, _parse_iso8601_utc

FIXTURE = Path(__file__).parent / "fixtures" / "posts_sample.json"


def test_parses_valid_entries_and_skips_broken() -> None:
    parser = PostsJsonParser()
    posts = list(parser.parse(FIXTURE))
    # Three valid entries; fourth is malformed and should be skipped.
    assert len(posts) == 3


def test_first_entry_fields() -> None:
    parser = PostsJsonParser()
    posts = list(parser.parse(FIXTURE))
    p = posts[0]
    assert p.back_path == "/Photos/user-123/post/aaaa.webp"
    assert p.front_path == "/Photos/user-123/post/bbbb.webp"
    assert p.caption == "hello world"
    assert p.location == (48.8566, 2.3522)
    assert p.taken_at.tzinfo is not None
    assert p.taken_at.astimezone(timezone.utc).year == 2023


def test_optional_fields_default_to_none() -> None:
    parser = PostsJsonParser()
    posts = list(parser.parse(FIXTURE))
    second = posts[1]
    assert second.caption is None
    assert second.location is None


def test_caption_without_location() -> None:
    parser = PostsJsonParser()
    posts = list(parser.parse(FIXTURE))
    third = posts[2]
    assert third.caption == "no gps here"
    assert third.location is None


def test_retake_counter_parsed() -> None:
    parser = PostsJsonParser()
    posts = list(parser.parse(FIXTURE))
    assert posts[0].retake_counter == 0
    assert posts[1].retake_counter == 1


def test_iso8601_trailing_z_only() -> None:
    dt = _parse_iso8601_utc("2022-07-08T09:33:33.729Z")
    assert dt.tzinfo is not None
    assert dt.astimezone(timezone.utc).isoformat() == "2022-07-08T09:33:33.729000+00:00"


def test_iso8601_explicit_offset_unchanged() -> None:
    dt = _parse_iso8601_utc("2022-07-08T11:33:33+02:00")
    assert dt.astimezone(timezone.utc).hour == 9
