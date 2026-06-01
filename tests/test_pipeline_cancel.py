"""`Reconstructor.run` honours the cooperative `should_cancel` hook."""

from __future__ import annotations

from pathlib import Path

from rebereal.config import Config
from rebereal.pipeline import build

FIXTURE = Path(__file__).parent / "fixtures" / "posts_sample.json"


def test_cancel_before_first_post_writes_nothing(tmp_path: Path) -> None:
    cfg = Config(export_root=tmp_path, output_root=tmp_path)
    recon = build(cfg)
    summary = recon.run(posts_path=FIXTURE, should_cancel=lambda: True)

    assert summary.cancelled is True
    assert summary.written == 0


def test_cancel_after_one_post_stops_loop(tmp_path: Path) -> None:
    cfg = Config(export_root=tmp_path, output_root=tmp_path)
    recon = build(cfg)

    # Cancel only once the second post is reached. The fixture's images don't
    # exist on disk, so the first post is skipped (not written) — what matters
    # is that the loop stops early and flags the run cancelled.
    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    summary = recon.run(posts_path=FIXTURE, should_cancel=should_cancel)

    assert summary.cancelled is True
    # Polled twice: allowed the first post, stopped before the second.
    assert calls["n"] == 2


def test_no_cancel_runs_to_completion(tmp_path: Path) -> None:
    cfg = Config(export_root=tmp_path, output_root=tmp_path)
    recon = build(cfg)
    summary = recon.run(posts_path=FIXTURE)

    assert summary.cancelled is False
