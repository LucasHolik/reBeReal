# reBeReal

Reconstruct importable photos from a BeReal data export.

reBeReal reads a BeReal export folder (`posts.json` + `Photos/`), composes each
post back into the classic BeReal look (back-camera frame + front-camera inset),
stamps each output with EXIF (date + GPS), XMP, and IPTC metadata, and writes
one JPEG per post organised by year.

The caption is written via XMP `dc:description` and IPTC `Caption-Abstract`
(the two channels Apple Photos and Google Photos actually read). GPS is
written as standard EXIF GPS tags and is only present for posts whose
`posts.json` entry has a `location` field — that's a minority of posts, so
only some of the imported BeReals will appear on the Photos map / Places
view. This is expected.

## Install

All work runs inside the `bereal` conda env:

```
conda activate bereal
pip install -e ".[dev]"
```

## Usage

### GUI

```
python main.py
```

Pick the export folder and an output folder, click **Preview** to render three
sample composites, then **Run** to process the full export.

### CLI

```
python -m rebereal --export ./Data --output ./Output
```

Useful flags: `--layout classic`, `--no-gps`, `--no-caption`, `--overwrite`, `-v`.

## Tests

```
pytest -q
```

## Layout

- `src/rebereal/` — core library (headless; no Tk import).
- `src/rebereal/gui/` — Tk wrapper; imports core, never the reverse.
- `tests/` — pytest scaffold.

Strategy plugins live under `layouts/`, `parsers/`, `metadata/`, and `naming/`;
new variants drop in without touching the orchestrator.
