# Stage97 — split the existing private Saturn Track1 into five independent ZIP files

## Why this is useful now

The already supplied original English v1.1 Saturn Track1 remains a single
**621,755,904-byte** file in the user's connected private Google Drive.
The connected ChatGPT Drive raw-file tool rejects files larger than
**268,435,456 bytes**, even though it can read the real CUE and Track2
(their SHA-256 digests independently matched the Stage02 pins).

Splitting Track1 into **separate ZIP files smaller than 256 MiB** lets each
archive be downloaded individually and reconstructs the original file with
a final complete SHA-256. The source disc is not compressed in place,
altered, repatched or posted to GitHub.

Use **five independent ZIP archives**, not one solid 7z volume: one missing
or corrupt ZIP must be diagnosable without having to interpret a multipart
archive format. Each ZIP contains one exact byte-range raw member and
uses ZIP_STORED without lossy transformations.

| File (example) | Uncompressed Track1 bytes |
| --- | ---: |
| track1-part-000.zip | 134,217,728 |
| track1-part-001.zip | 134,217,728 |
| track1-part-002.zip | 134,217,728 |
| track1-part-003.zip | 134,217,728 |
| track1-part-004.zip | 84,884,992 |

ZIP headers add only a small amount of overhead. Each independently
downloadable archive remains far below 268,435,456 bytes.

Also upload **track1-private-parts.json**, generated last. That private
manifest stores the original Track1 filename, total size, Stage02 SHA-256
and expected size/SHA-256 of each ZIP and its contained raw part.

## Alternative: do it inside your existing private Google Drive

If the original 621,755,904-byte file is **only** in Google Drive, use
the optional prepared notebook:

[Stage97 private Drive Colab notebook](../notebooks/STAGE97_SPLIT_TRACK1_FROM_PRIVATE_DRIVE.ipynb)

Open it in your **own** Google Colab session, review the notebook code,
then explicitly authorize Drive mount. The notebook scans your private
`MyDrive/VH-Saturn` folder for exactly one file with the Stage02 Track1
size, verifies its *complete* Stage02 SHA-256, splits it on Colab's
temporary filesystem and copies each ZIP to `VH-Saturn/Track1-parts`.
It verifies every uploaded ZIP's digest and copies the manifest last.

The original Track1 remains unchanged in Drive. No local download/upload
through your own computer is needed, although the notebook must still
read the file inside your authorized Drive mount. This notebook has
**not** been executed against the original image here; Drive-mount
filesystem behavior may require adjustment in your Colab session.

**Privacy:** Mounting Drive grants the Colab notebook broad access to
files in the account. Only run reviewed code in your own trusted
session; do not share auth tokens, private output, or Colab notebooks
with mounted Drive access publicly.

## Procedure on a trusted local computer

Have the **already owned original Track1** available as a readable local
file. No second copy needs to be provided through ChatGPT. Use the existing
public repository's Stage97 tool, but keep all source and output paths
*outside* the Git checkout.

```bash
mkdir -m 700 "/private/vh-saturn-parts"
python3 -m tools.saturn_private_track1_split_zip split \
  --track1 "/private/original/EXACT_TRACK1_FILENAME.bin" \
  --parts-dir "/private/vh-saturn-parts" \
  --chunk-mib 128
```

Paths above are placeholders. The splitter verifies the **complete
original Track1 against Stage02 SHA-256 and size before and after the
operation**, without changing it, and refuses an absent/mismatched source.
It writes five ZIPs and the manifest into a fresh protected 0700 folder.
If any ZIP creation fails, partial files are removed. It prints only
counts, not disc bytes, paths, file hashes, catalog IDs or private links.

Upload all **six generated files** (five ZIPs plus the JSON) to a *private*
Google Drive folder, ideally `VH-Saturn/Track1-parts`. Keep the original
CUE and Track2 in their existing private Drive folder; do not upload
game data to GitHub, issues or public CI and do not change sharing to
"anyone with the link".

## After each archive is available locally again

Obtain the same six private files in one protected 0700 local folder.
Use the exact original Track1 filename in the output path (the same
basename as before splitting and as referenced by the original CUE):

```bash
mkdir -m 700 "/private/vh-saturn-reassembled"
python3 -m tools.saturn_private_track1_split_zip join \
  --parts-dir "/private/vh-saturn-parts-downloaded" \
  --output "/private/vh-saturn-reassembled/EXACT_TRACK1_FILENAME.bin"
```

The verifier checks that there are exactly five ZIPs and one JSON,
validates every archive SHA-256 and byte count, refuses ZIPs with extra
members, nonmatching entries or unexpected compression, checks each
raw part against its own digest, then checks **the final entire Track1
against the pre-existing Stage02 SHA-256**. Only after all checks pass
does it reveal a private read-only file (mode 0400). It will never
overwrite an existing output or leave a partial success file.

The reassembled file can then be passed to the existing Stage93/94
preflight along with the original unchanged CUE and Track2.

## Why this does not yet prove original gameplay

These archives have **not** been generated from the real Track1 here,
because the current connected Drive tool cannot obtain its bytes in
one call. The actual file must be split by the user on a trusted device
or in an authorized private Drive-mounted environment. The scripts
themselves have public CI tests using only a small invented 2352-byte
sector-aligned file. No original Track1 chunks, ZIPs or full CUE appear
in GitHub Actions.

The earlier Stage92 local OAuth/Range alternative remains available
if splitting cannot be performed on a locally held copy. Both options
only establish **media identity**. They do not authenticate the original
Japanese master, prove Sega Saturn game boot or observe the first
battle; the genuine source/capture acceptance gate remains Issue #11.

Google Drive connector compatibility for individually uploaded ZIPs
should be tested with the actual small files before claiming successful
remote reconstruction; current tooling has not retrieved these ZIPs.
