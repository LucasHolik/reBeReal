# BeReal Data Export — Format Reference

Reference for the structure of a BeReal data export as shipped on
**2026-05-18**. The export format is not officially documented and is
subject to change; this project targets only the layout described here.

A BeReal export arrives as a single folder containing JSON metadata at
the root and media under `Photos/` and `conversations/`. This document
describes every file and folder in that export, the shape of every JSON
record, and which fields are required vs. optional.

> Field-presence classifications below ("required" / "optional") were
> determined empirically against a real export. Fields marked required
> were present in every record observed; this is not a guarantee that
> they cannot be absent in another account's export. Treat all fields
> defensively when consuming the data.

---

## 1. Top-level layout

```
<export>/
├── posts.json              ← every BeReal the user posted (primary source)
├── memories.json           ← the same posts, alternative schema
├── comments.json           ← comments the user wrote on others' posts
├── realmojis.json          ← the user's reusable realmoji templates
├── friends.json            ← current friend list
├── friend-requests.json    ← pending incoming friend requests
├── blocked-users.json      ← blocked users
├── user.json               ← account metadata
├── push-settings.json      ← push-notification opt-ins
├── push-tokens.json        ← historical device registrations
├── terms.json              ← permission / ToS acceptance log
├── conversations/          ← DMs (one subfolder per conversation)
│   └── <conversationId>/
│       ├── chat_log.json
│       └── *.webp          ← in-chat image attachments
└── Photos/
    ├── bereal/             ← BeReal photos for posts before 2022-11-25
    ├── post/               ← BeReal photos for posts from 2022-11-25 on
    ├── profile/            ← profile pictures
    └── realmoji/           ← realmoji reaction selfies
```

There is no top-level manifest. The two photo folders (`bereal/` and
`post/`) reflect a single backend storage cutover on **2022-11-25**.
Every post before that date is in `bereal/`; every post from that date
onward is in `post/`. The JSON records identify the correct folder for
each post via the `path` field of the embedded media object.

---

## 2. The "media object" shape

Many records embed an image as the same nested object. It is documented
once here; below, "media object" refers to this shape:

```jsonc
{
  "bucket": "storage.bere.al", // also observed: "us1-storage.bere.al"
  "path": "/Photos/<userId>/<folder>/<filename>.<ext>",
  "height": 2000, // integer (px); see note below
  "width": 1500, // integer (px); see note below
  "mediaType": "image", // only "image" observed
  "mimeType": "image/jpeg", // or "image/webp"; sometimes omitted
}
```

Notes:

- `path` typically begins with `/Photos/<userId>/`, but a minority of
  entries lack the leading slash (a stretch of the `bereal/`-era posts
  and every entry in `realmojis.json`). The leading `<userId>` segment
  does not exist on disk — the local file lives at
  `<export>/Photos/<folder>/<filename>`. Strip the first two segments
  of `path` to obtain the on-disk location (this works for both the
  leading-slash and no-leading-slash forms).
- `bucket` is usually `storage.bere.al`, but a minority of posts use
  `us1-storage.bere.al`. Consumers that only need the on-disk file can
  ignore `bucket` entirely.
- In `user.json` specifically, `height` and `width` are encoded as JSON
  **strings** rather than integers. Every other media object uses
  integers.
- `mimeType` is omitted from realmoji `media` objects.

---

## 3. `posts.json`

A JSON array of post objects, ordered oldest-first. One element per
BeReal the user has ever posted. This is the primary source of truth
for reconstruction.

### Fields

| Field           | Type                      | Presence | Notes                                                                                                                                                                                                        |
| --------------- | ------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `primary`       | media object              | required | **Back camera** (main shot).                                                                                                                                                                                 |
| `secondary`     | media object              | required | **Front camera** (selfie). In the `bereal/` era both files of a pair share a UUID/timestamp and the front-camera file has a `-secondary` suffix. In the `post/` era the two files have unrelated random IDs. |
| `takenAt`       | string (ISO-8601 UTC, ms) | required | Shutter time, e.g. `"2022-07-08T09:33:33.729Z"`.                                                                                                                                                             |
| `retakeCounter` | integer                   | required | Number of times the BeReal was retaken before being posted. Small non-negative integer.                                                                                                                      |
| `visibility`    | string array              | required | Observed value: `["friends"]`. Public-feed posts presumably produce `["public"]` but this has not been confirmed.                                                                                            |
| `caption`       | string                    | optional | Free text. May contain emoji.                                                                                                                                                                                |
| `location`      | object                    | optional | `{ "latitude": <float>, "longitude": <float> }` in decimal degrees.                                                                                                                                          |

### Fields NOT present in `posts.json` (but present in `memories.json`)

`isLate`, `berealMoment`, `music`, `date`, `takenTime`. Read
`memories.json` (§4) for any of these.

### Camera-to-field mapping

`primary` is the back camera (the large background in the classic
composite); `secondary` is the front camera (the small selfie inset).
The aliases in `memories.json` are clearer:

- `posts.primary` ↔ `memories.backImage`
- `posts.secondary` ↔ `memories.frontImage`

---

## 4. `memories.json`

A JSON array containing the same posts as `posts.json`, with a
different schema. `posts.json` is strictly oldest-first by `takenAt`;
`memories.json` is sorted by the `date` field, descending. Multiple
posts can share a `date`, so within-day `takenTime` order is not
guaranteed and the two files are not exact mirrors of each other. To
join the two files, match on `posts[i].takenAt == memories[j].takenTime`
— do not rely on the array index. Either file can drive reconstruction;
each exposes a few fields the other does not.

### Fields

| Field          | Type                            | Presence | Notes                                                                        |
| -------------- | ------------------------------- | -------- | ---------------------------------------------------------------------------- |
| `backImage`    | media object                    | required | Equivalent to `posts[i].primary`.                                            |
| `frontImage`   | media object                    | required | Equivalent to `posts[i].secondary`.                                          |
| `date`         | string (ISO-8601, midnight UTC) | required | The BeReal calendar day, e.g. `"2025-04-20T00:00:00.000Z"`.                  |
| `takenTime`    | string (ISO-8601 UTC, ms)       | required | Equivalent to `posts[i].takenAt`.                                            |
| `isLate`       | boolean                         | required | `true` if the post was published after the daily notification window.        |
| `berealMoment` | string (ISO-8601 UTC, ms)       | required | The day's official notification time (when the "Time to BeReal" push fired). |
| `caption`      | string                          | optional | Same as `posts.json`.                                                        |
| `location`     | `{ latitude, longitude }`       | optional | Same as `posts.json`.                                                        |
| `music`        | object (see below)              | optional | Music track attached to the post. Rare.                                      |

### `music` object

```jsonc
{
  "track": "<song title>",
  "artist": "<artist name>",
  "openUrl": "https://open.spotify.com/track/<id>",
  "artwork": "https://i.scdn.co/image/<hash>",
  "providerId": "<provider track ID>",
  "isrc": "<ISRC code>",
  "visibility": "public",
  "audioType": "track",
  "provider": "spotify", // or "appleMusic"
}
```

### Fields NOT present in `memories.json` (but present in `posts.json`)

`retakeCounter`, `visibility`.

---

## 5. `comments.json`

A JSON array of comments the user wrote on **other accounts'** posts
(not comments left on the user's own BeReals).

```jsonc
{ "postId": "<server-side post ID>", "content": "<text>" }
```

| Field     | Type   | Notes                                                                                                                                                                                  |
| --------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `postId`  | string | Server-side post ID. Cannot be cross-referenced to any other file in the export — the posts in question are not the user's own and so do not appear in `posts.json` / `memories.json`. |
| `content` | string | Comment text. May contain emoji.                                                                                                                                                       |

The record contains no timestamp, no author (the author is implicitly
the exporting user), and no target-user identifier. Comments are
effectively orphaned data.

---

## 6. `realmojis.json`

A JSON array of the user's reusable realmoji selfies — the small set of
canned reaction faces captured once and re-used to react to friends'
BeReals.

```jsonc
{
  "createdAt": "2023-02-10T09:49:59.107Z",
  "emoji": "😍",
  "isEnabled": true,
  "media": {
    "bucket": "storage.bere.al",
    "path": "Photos/<userId>/realmoji/<userId>-realmoji-<slug>-<unixSeconds>.<ext>",
    "height": 500,
    "width": 500,
    "mediaType": "image",
  },
}
```

| Field       | Type         | Notes                                                                                                                                                           |
| ----------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `createdAt` | string (ISO) | When the selfie was captured.                                                                                                                                   |
| `emoji`     | string       | Unicode emoji this realmoji corresponds to.                                                                                                                     |
| `isEnabled` | boolean      | Whether the realmoji is currently in the active set.                                                                                                            |
| `media`     | media object | File under `Photos/realmoji/`. Filename embeds a slug (e.g. `heartEyes`, `like`, `surprised`, `laughing`, `instant`) and a Unix timestamp. No `mimeType` field. |

Note: `realmojis.json` only describes the small set of **template**
selfies. The much larger set of files actually present in
`Photos/realmoji/` includes every realmoji the user ever posted on a
friend's BeReal; that historical usage carries no metadata in the
export.

---

## 7. `friends.json`

A JSON array of the user's current friends.

```jsonc
{
  "friendUsername": "<handle>",
  "friendFullname": "<display name>",
  "createdAt": "2024-03-08T11:54:18.252Z",
}
```

| Field            | Type         | Notes                                            |
| ---------------- | ------------ | ------------------------------------------------ |
| `friendUsername` | string       | BeReal handle.                                   |
| `friendFullname` | string       | Display name. May be empty or only a first name. |
| `createdAt`      | string (ISO) | When the friendship was established.             |

Records contain no user ID, so they cannot be joined to
`friend-requests.json` or to message authors in
`conversations/*/chat_log.json` (both of which key on user IDs only).

---

## 8. `friend-requests.json`

A JSON array of **pending incoming** friend requests only. Sent
requests and historical (accepted/declined) requests are not included.

```jsonc
{
  "fromUserId": "<sender user ID>",
  "status": "pending",
  "createdAt": "2026-03-22T16:32:35.853Z",
  "updatedAt": "2026-03-22T16:32:35.853Z",
}
```

| Field        | Type         | Notes                                             |
| ------------ | ------------ | ------------------------------------------------- |
| `fromUserId` | string       | Sender's user ID. Not joinable to `friends.json`. |
| `status`     | string       | Only `"pending"` observed.                        |
| `createdAt`  | string (ISO) | Request time.                                     |
| `updatedAt`  | string (ISO) | Equal to `createdAt` for pending requests.        |

---

## 9. `blocked-users.json`

A JSON array of blocked-user records. The record shape was not
observable in the reference export (the array was empty).

---

## 10. `user.json`

A single JSON object describing the account.

```jsonc
{
  "username": "<handle>",
  "fullname": "<display name>",
  "birthdate": { "year": 0000, "month": 0, "day": 0 },
  "phoneNumber": "<E.164 number>",
  "clientVersion": "<app version>",
  "device": "<device model + OS>", // e.g. "iPhone17,1 26.4.2"
  "deviceId": "<UUID>",
  "profilePicture": {
    "path": "/Photos/<userId>/profile/<file>.webp",
    "bucket": "storage.bere.al",
    "height": "999", // ← string here, integers elsewhere
    "width": "999",
  },
  "location": "<free-text city / region>", // not lat/lon
  "platform": 1, // integer; presumed 1 = iOS
  "countryCode": "GB",
  "language": "en",
  "timezone": "Europe/London",
  "region": "europe-west",
  "createdAt": "2022-07-07T11:20:34.055Z",
}
```

`profilePicture.path` points only at the **current** profile picture.
Older profile pictures present in `Photos/profile/` have no metadata
referencing them.

---

## 11. `push-settings.json`

A single object of booleans recording which push-notification
categories are enabled.

```jsonc
{
  "late": true,
  "comment": true,
  "mention": true,
  "friendRequest": true,
  "realmoji": true,
}
```

Not relevant to reconstruction; included for completeness.

---

## 12. `push-tokens.json`

A JSON array of device registrations across the account's lifetime —
one entry per (device, client-version) registration event. The actual
push-token strings are not included; only the device metadata BeReal
captured at registration time.

```jsonc
{
  "deviceId": "<UUID>",
  "clientVersion": "<app version>",
  "language": "en",
  "region": "europe-west",
  "platform": "ios", // string here; integer in user.json
  "timezone": "Europe/London",
}
```

Duplicate entries may appear (the same device re-registering on a new
version).

---

## 13. `terms.json`

A JSON array of permission / ToS acceptance events. The list mixes
"legal" agreements (terms of service, privacy policy) with OS-level
permissions (camera, GPS, microphone, photo library, contacts, push,
screen recording).

```jsonc
{
  "code": "gps",
  "status": "ACCEPTED", // or "DECLINED" or "UNKNOWN"
  "signedAt": "2022-07-07T12:16:03.674Z",
  "version": 1,
  "termUrl": "https://bere.al",
}
```

| Field      | Type    | Notes                                                                 |
| ---------- | ------- | --------------------------------------------------------------------- |
| `code`     | string  | Permission or agreement identifier (see below).                       |
| `status`   | string  | One of `ACCEPTED`, `DECLINED`, `UNKNOWN`.                             |
| `signedAt` | string  | ISO timestamp. **Absent when `status` is `UNKNOWN`.**                 |
| `version`  | integer | Agreement version.                                                    |
| `termUrl`  | string  | Either the generic `https://bere.al` or a specific terms/privacy URL. |

Codes observed: `gps`, `memories`, `terms`, `privacy`, `camera`,
`contacts`, `show-friends-to-friends`, `microphone`, `apple-music`,
`photo-library-read`, `photo-library-write`, `screen-recording`,
`push-notifications`. The set may vary across accounts.

Not relevant to reconstruction.

---

## 14. `conversations/`

One subfolder per DM conversation. The subfolder name is the
`conversationId`. Each subfolder contains:

- exactly one `chat_log.json`
- zero or more `*.webp` files — image attachments referenced by
  messages in the chat log

### `chat_log.json`

A single object:

```jsonc
{
  "conversationId": "<id>",
  "createdAt":      "<ISO timestamp>",
  "messages": [ ... ]                     // ordered oldest → newest
}
```

### Message entries

Each entry in `messages` carries up to four fields:

| Field       | Type         | Presence | Notes                                                                                                                                                                                                                               |
| ----------- | ------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`        | string       | required | Per-conversation sequential ID (`"1"`, `"2"`, ...). Gaps occur (likely deleted messages).                                                                                                                                           |
| `userId`    | string       | usually  | Author. Absent on system / tombstone entries.                                                                                                                                                                                       |
| `createdAt` | string (ISO) | required | May be the sentinel `"0001-01-01T00:00:00.000Z"` for tombstones.                                                                                                                                                                    |
| `message`   | string       | optional | For **text** messages, the UTF-8 message body. For **attachment** messages, a binary protobuf-like blob (length-prefixed) that references the conversation's `.webp` files internally. There is no separate `attachmentPath` field. |

Three observed entry shapes:

- `{id, userId, createdAt, message}` — normal text or attachment message.
- `{id, userId, createdAt}` — message exists but body has been stripped
  (deleted or unrenderable type).
- `{id, createdAt}` with the sentinel zero-date — placeholder /
  tombstone.

Attachments cannot be cleanly resolved without parsing the protobuf
blob. Attachment files in the conversation folder are named with a
leading numeric prefix that mirrors a message ID
(e.g. `102-yUFQneNnsKwIi_4wgTPVE.webp`), making a heuristic match on
that prefix possible.

---

## 15. `Photos/`

Four subfolders. None contain a manifest; metadata is exclusively in
the JSON files described above.

### `Photos/bereal/`

- Holds BeReals posted before the 2022-11-25 storage cutover.
- Mixed `.jpg` and `.webp` files.
- Filename pattern:
  ```
  <uuid>-<unixSeconds>.<ext>            ← back camera (= posts.primary)
  <uuid>-<unixSeconds>-secondary.<ext>  ← front camera (= posts.secondary)
  ```
  Example: `02c6f1c9-66ea-4f1c-8d09-1132a9833012-1667129145.webp`.
- The two files of a pair always share UUID and timestamp; the
  `-secondary` suffix is the only structural differentiator.

### `Photos/post/`

- Holds BeReals posted from 2022-11-25 onward.
- All `.webp`.
- Filename pattern: a short, opaque, randomly-generated ID, e.g.
  `2m7OJZqbD1bgsYas.webp`. The front and back files of a single post
  have **unrelated** IDs — they can only be paired via the JSON.

### `Photos/profile/`

- One `.webp` per historical profile picture.
- Only the current profile picture is referenced (via
  `user.json.profilePicture.path`); older files are orphaned in
  metadata.

### `Photos/realmoji/`

- `.webp` files; typically thousands of them.
- A small minority (the user's "template" realmojis) are referenced
  by `realmojis.json`. The remainder represent realmojis sent on
  friends' BeReals over the account's lifetime and have no
  accompanying metadata.
- The template files use the named pattern
  `<userId>-realmoji-<slug>-<unixSeconds>.<ext>`; non-template files
  use opaque random IDs.

---

## 16. Coverage and integrity

The export is not guaranteed to be internally consistent. Real exports
have been observed to include:

- **Missing photos** — a small number of `posts.json` entries reference
  image paths that do not exist on disk. The matching pair member is
  usually still present. Consumers should treat each photo as
  independently optional and skip (or warn about) any BeReal where one
  or both files cannot be loaded.
- **Orphaned photos** — a small number of files exist in `Photos/`
  without any corresponding `posts.json` entry. These are most likely
  posts that were later deleted from the account but whose underlying
  blobs were not garbage-collected from storage.
- `posts.json` and `memories.json` consistently agree: every entry in
  one has a 1:1 counterpart in the other, joinable by timestamp
  (`takenAt` ↔ `takenTime`). Array index is not a valid join key (see §4).

---

## 17. Cross-file joinability

What can be joined:

- `posts.json` ↔ `memories.json` — by **timestamp** (`takenAt` ↔ `takenTime`). The two files cover identical content but in opposite order (`posts.json` oldest-first, `memories.json` newest-first), so array index is not a valid join key.
- `posts.json` / `memories.json` → image files — by stripping the
  first two segments of the media-object `path`.
- `realmojis.json` → template files in `Photos/realmoji/` — by `media.path`.
- `user.json.profilePicture.path` → the current file in `Photos/profile/`.

What cannot be joined within the export:

- `comments.json.postId` — references posts owned by other accounts;
  no corresponding records appear anywhere in the export.
- `friends.json` entries carry no user ID, so they cannot be joined to
  `friend-requests.json.fromUserId` or to message authors in
  `conversations/*/chat_log.json`.
- DM attachments are embedded inside the `message` protobuf blob
  rather than referenced by an explicit field.
- Non-template realmojis in `Photos/realmoji/` have no metadata: no
  recipient, no timestamp, no associated post.
- Historical profile pictures in `Photos/profile/` have no metadata.

These gaps do not affect BeReal reconstruction (which depends only on
`posts.json` plus `Photos/bereal/` and `Photos/post/`) but constrain
any broader use of the export.
