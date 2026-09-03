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

reBeReal never talks to BeReal — it only reads an export you already hold.
BeReal has no self-serve "download my data" button, so getting one means making
a formal request. Two routes, both free under your GDPR right of access:

**In the app** — usually the faster one:

1. Tap your profile picture (bottom right), then the gear icon for **Settings**.
2. Scroll to the **About** section and tap **Help**.
3. Tap **Select Topic** and choose the option about requesting a copy of your
   data. If it isn't listed, go **Contact us → Ask a Question →
   Troubleshooting → Other → Still need help?** instead.
4. State that you are making a subject access request under GDPR Articles 15
   and 20, and ask for all personal data — photos and associated metadata
   included — in a machine-readable format.

**By email** — write to BeReal's Data Protection Team at dpo@bere.al. They do
not always hold your email address, so expect to be asked to prove the request
is yours: have your username, phone number (with country code) and date of
birth to hand.

BeReal have 30 days to respond; in practice the file tends to come back within a
couple of days. Ask for it first — the wait is the slow part of this.

What arrives is a `.zip` of your photos as WebP (bar some JPEGs in the earliest
folder), none of them carrying any embedded metadata; the dates and locations
sit in a separate JSON file. Putting the two back together
is what reBeReal is for. Out of everything in the archive it reads three things:

```
<export>/
├── posts.json          ← the only metadata file reBeReal reads
└── Photos/
    ├── bereal/         ← BeReals posted before 2022-11-25
    └── post/           ← BeReals posted from 2022-11-25 on
```

Everything else — `memories.json`, `conversations/`, `Photos/realmoji/`, the
account metadata — is ignored; leave it in place.

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
