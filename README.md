# reBeReal

Reconstruct importable photos from a BeReal data export.

reBeReal reads a BeReal export folder (`posts.json` + `Photos/`), composes each
post back into the classic BeReal look (back-camera frame + front-camera inset),
stamps each output with EXIF (date + GPS), XMP, and IPTC metadata, and writes
one JPEG per post organised by year.

The caption is written via XMP `dc:description` and IPTC `Caption-Abstract`
(the two channels Apple Photos and Google Photos actually read). GPS is
written as standard EXIF GPS tags and is only present for posts whose
`posts.json` entry has a `location` field.

![reBeReal landing screen](assets/start-page.webp)

## Getting your export

reBeReal never talks to BeReal — it only reads an export you already hold. If
you don't have one yet, BeReal will send you one free of charge under your GDPR
right of access. In the app: tap your profile picture, then the gear icon, then
**Help** (under *About*), and pick the topic **"I'd like to request a copy of my
data"**. The reply arrives in the same in-app help thread with a download link;
turnaround is typically hours to a couple of days, though BeReal have up to 30
days to comply. Emailing contact@bere.al is the documented fallback if your
build of the app offers no such topic. Ask for it first — the wait is the slow
part of this.

The link gives you a `.zip`. Out of everything in it, reBeReal reads three
things:

```
<export>/
├── posts.json          ← the only metadata file reBeReal reads
└── Photos/
    ├── bereal/         ← BeReals posted before 2022-11-25
    └── post/           ← BeReals posted from 2022-11-25 on
```

Everything else — `memories.json`, `conversations/`, `Photos/realmoji/`, the
account metadata — is ignored; leave it in place. If BeReal send more than one
file, the one you want is the archive containing `posts.json`.

- **GUI**: hand it the `.zip` directly (it extracts it for you) or the unzipped
  folder. Either may sit up to two levels deep inside a wrapper folder — the
  export root is found for you.
- **CLI**: unzip first. `--export` must point at the folder that *directly*
  contains `posts.json`.

Nothing is uploaded and nothing phones home: the export is read from disk, the
composites go to the output folder you pick, and that is the whole of it.

[`EXPORT_FORMAT.md`](EXPORT_FORMAT.md) documents the export in full — every file,
every field. The parser targets the format as shipped on 2026-05-18; BeReal do
not document it and may change it, so an export in a different shape may not
parse.

## Install

The recommended setup is a dedicated conda environment, then an editable install
with the GUI extra:

```
conda create -n rebereal python=3.12
conda activate rebereal
pip install -e ".[dev,gui]"
```

## Usage

### GUI

```
python main.py
```

The app opens on a landing screen: drop your BeReal export **folder or `.zip`**
onto the drop zone (or use **Choose folder… / Choose .zip…**). A zip is
extracted in the background with a progress bar. Once it loads, the working UI
appears and three sample composites preview automatically, re-rendering when you
change the layout, resolution, or JPEG quality. Pick an **output folder** and
click **Run** to process the full export. **Restart** returns to the landing
screen to load a different export.

![reBeReal working UI with automatic previews](assets/main-page.webp)

### CLI

```
python -m rebereal --export ./Data --output ./Output
```

Useful flags: `--layout classic`, `--no-gps`, `--no-caption`, `-v`.

Three layouts are implemented (pass the key to `--layout` or pick it in the GUI):

- `classic` — the BeReal-style back-camera frame with the front-camera inset.
- `inverted_classic` — the front camera fills the frame with the back camera as
  the inset.
- `side_by_side` — both cameras at equal size, stitched horizontally (back | front).

The remaining variants — separate files per post and classic-plus-originals — are
planned and slot into the `layouts/` plugin registry without touching the
orchestrator.

Output quality:

- `--resolution` — output size as a fraction of source, `0.01`–`1.0`; keeps
  aspect ratio (default `1.0` = full source resolution).
- `--jpeg-quality` — JPEG quality `1`–`100` (default `80`). Higher isn't always
  visibly better: past ~85 the quality gain is hard to see but the file size
  keeps climbing.

Both controls are also available in the GUI.

## Tests

```
pytest -q
```

## Layout

- `src/rebereal/` — core library (headless; no GUI import).
- `src/rebereal/gui/` — Qt (PySide6) wrapper; imports core, never the reverse.
- `tests/` — pytest scaffold.

Strategy plugins live under `layouts/`, `parsers/`, `metadata/`, and `naming/`;
new variants drop in without touching the orchestrator.

## License

[MIT](LICENSE) © Lucas Holik
